#!/usr/bin/env python3
"""T3 — recompute every calculation of an opgave's correctievoorschrift (specs/34 §3, CC).

Usage: calc_check.py <run_dir> --opgave <id> [--subjects <dir>]

Reads 33_items/<opgave>.json. Every `calc.expr` is evaluated with a safe evaluator (nlnum.safe_eval: numbers, names,
+ - * / ** ( ), min, max, round, abs, sum) over `data` plus the earlier calc names of the opgave (also across
vragen, in vraag order). A calc result is rounded per `round`/`rounding` (half_up default, up, down); later calcs use
the rounded value, as the correctievoorschrift shows it. The rounded result in Dutch notation (with the € / %
of `shown`) must equal `shown`. Fails on: a wrong result, an unknown name, a duplicate name or a name that is also a
data key, an unused calc (not used by a later calc, not a scorepunt's calc_ref and its shown value not in the model
answer), and a calc_ref that points to no calc. Writes 33_checks/<opgave>.calc.json (the computed values, used by
figures.py and solver_compare.py) and prints the report.
"""
from __future__ import annotations

import sys
from pathlib import Path

from nlnum import EvalError, format_nl, names_in, round_mode, safe_eval, shown_value
from tcommon import Report, load_json, save_json
from toetsrun import opt


def evaluate(items: dict) -> tuple[dict, list[tuple[str, str]]]:
    """name → {value, raw, vraag_id, shown}; errors as (vraag_id/name, message)."""
    data = items["data"]
    names = dict(data)
    out, errs = {}, []
    for v in sorted(items["vragen"], key=lambda x: x["number"]):
        for c in v["cv"]["calc"]:
            tag = f"{v['vraag_id']} {c['name']}"
            if c["name"] in data:
                errs.append((tag, f"calc name '{c['name']}' is also a data key"))
                continue
            if c["name"] in out:
                errs.append((tag, f"calc name '{c['name']}' defined twice"))
                continue
            try:
                raw = safe_eval(c["expr"], names)
            except EvalError as e:
                errs.append((tag, str(e)))
                continue
            val = round_mode(raw, c.get("round"), c.get("rounding"))
            names[c["name"]] = val
            out[c["name"]] = {"value": val, "raw": raw, "vraag_id": v["vraag_id"], "shown": c["shown"],
                              "round": c.get("round"), "expr": c["expr"]}
    return out, errs


def expected_shown(value: float, shown: str, digits: int | None) -> str:
    _, prefix, suffix, sd = shown_value(shown)
    return f"{prefix}{format_nl(value, digits if digits is not None else sd)}{suffix}"


def main(argv: list[str]) -> None:
    if len(argv) < 2 or not opt(argv, "--opgave"):
        print(__doc__)
        sys.exit(2)
    R, oid = Path(argv[1]), opt(argv, "--opgave")
    rep = Report(f"calc_check {oid}")
    items = load_json(R / "33_items" / f"{oid}.json")
    vals, errs = evaluate(items)
    for tag, msg in errs:
        rep.fail("CC", f"{tag}: {msg}")
    used = set()
    for v in items["vragen"]:
        for c in v["cv"]["calc"]:
            used |= names_in(c["expr"])
    for v in items["vragen"]:
        refs = {s.get("calc_ref") for s in v["cv"]["scorepunten"] if s.get("calc_ref")}
        for r in sorted(refs):
            if r not in vals and not any(r == c["name"] for c in v["cv"]["calc"]):
                rep.fail("CC", f"{v['vraag_id']}: scorepunt calc_ref '{r}' points to no calc")
        used |= refs
        for c in v["cv"]["calc"]:
            tag = f"{v['vraag_id']} {c['name']}"
            if c["name"] not in vals:
                continue
            try:
                exp = expected_shown(vals[c["name"]]["value"], c["shown"], c.get("round"))
            except ValueError as e:
                rep.fail("CC", f"{tag}: shown '{c['shown']}' is not a Dutch number ({e})")
                continue
            if exp.replace(" ", "") != c["shown"].replace(" ", "").replace(" ", ""):
                rep.fail("CC", f"{tag}: {c['expr']} = {format_nl(vals[c['name']]['raw'], None)} → '{exp}', "
                               f"but the cv shows '{c['shown']}'")
            in_answer = c["shown"].replace("€", "").strip() in v["cv"]["model_answer"]
            if c["name"] not in used and not in_answer:
                rep.fail("CC", f"{tag}: calc is not used (no later calc, no calc_ref, not in the model answer)")
    save_json(R / "33_checks" / f"{oid}.calc.json", {"opgave_id": oid, "values": vals})
    rep.info("CC", f"{len(vals)} calculations recomputed")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
