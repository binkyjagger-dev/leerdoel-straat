#!/usr/bin/env python3
"""Validate 11_method_units.json (specs/11 §4).

Usage: validate_method.py <run_dir> [--chapters 1,2]
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from mcommon import Report, load_json, validate_schema


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("validate_method")
    data = load_json(run_dir / "11_method_units.json")
    for e in validate_schema(data, "method_units.schema.json"):
        rep.fail("MS1", e)
    if rep.failed:
        rep.print_and_exit()
    units = data["units"]
    ids = [u["unit_id"] for u in units]
    for uid, n in Counter(ids).items():
        if n > 1:
            rep.fail("MS1", f"duplicate unit_id {uid}")
    idset = set(ids)
    for u in units:
        if u["parent_id"] is not None and u["parent_id"] not in idset:
            rep.fail("MS1", f"{u['unit_id']}: parent {u['parent_id']} missing")
        if u["kind"] in ("paragraaf", "deelvraag"):
            if not u.get("text_ref"):
                rep.fail("MS1", f"{u['unit_id']}: {u['kind']} without text_ref")
            elif not (run_dir / u["text_ref"]).exists():
                rep.fail("MS1", f"{u['unit_id']}: text file {u['text_ref']} missing")
            elif len((run_dir / u["text_ref"]).read_text(encoding="utf-8").strip()) < 20:
                rep.warn("MS1", f"{u['unit_id']}: text shorter than 20 chars")
        if u["kind"] == "paragraaf" and u.get("order") is None:
            rep.fail("MS1", f"{u['unit_id']}: paragraaf without order")
        if u.get("page_from") and u.get("page_to") and u["page_to"] < u["page_from"]:
            rep.fail("MS1", f"{u['unit_id']}: page_to < page_from")
    paras = sorted((u for u in units if u["kind"] == "paragraaf"), key=lambda u: u["order"])
    orders = [u["order"] for u in paras]
    if orders != sorted(set(orders)):
        rep.fail("MS1", "paragraph order values are not strictly increasing/unique")
    kinds = Counter(u["kind"] for u in units)
    rep.info("MS1", f"{dict(kinds)}; extraction={data['method']['text_extraction']}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
