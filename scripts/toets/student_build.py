#!/usr/bin/env python3
"""T4 — the student version per opgave for the blind solver and the labellers (specs/33 §3 T4).

Usage: student_build.py <run_dir> [--opgave <id>]

Writes 34_student/<opgave>.md from 33_items/<opgave>.json: title, intro, the vragen ("**2p 3** stem"),
the informatiebronnen (text, table, figure path) and the uitwerkbijlage. No correctievoorschrift, no data block,
no writer notes, no blueprint content. Figures point to figures/<id>.png (student version, without answer lines);
a game_matrix figure with a `table` is written as a Markdown table.
"""
from __future__ import annotations

import sys
from pathlib import Path

from tcommon import load_json
from toetsrun import ToetsRun, opt


def md_table(rows: list[list]) -> list[str]:
    if not rows:
        return []
    rows = [[("" if c is None else str(c)) for c in r] for r in rows]
    w = max(len(r) for r in rows)
    rows = [r + [""] * (w - len(r)) for r in rows]
    return ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w] + ["| " + " | ".join(r) + " |" for r in rows[1:]]


def build(R: Path, it: dict, number: int) -> str:
    figs = {f["figure_id"]: f for f in it["figures"]}
    L = [f"# Opgave {number} {it['title']}", "", it["intro"], ""]
    for v in sorted(it["vragen"], key=lambda x: x["number"]):
        L += [f"**{v['points']}p {v['number']}** {v['stem']}", ""]
    if it["sources"]:
        L += ["## Informatiebronnen", ""]
    for s in sorted(it["sources"], key=lambda x: x["n"]):
        L += [f"### Informatiebron {s['n']} {s['title']}", ""]
        if s.get("text"):
            L += [s["text"], ""]
        if s.get("table"):
            L += md_table(s["table"]) + [""]
        if s.get("figure_id"):
            f = figs.get(s["figure_id"], {})
            if f.get("spec", {}).get("type") == "game_matrix" and f["spec"].get("table"):
                L += md_table(f["spec"]["table"]) + [""]
            else:
                L += [f"![{s['title']}](../figures/{s['figure_id']}.png)", ""]
    ub = [v for v in sorted(it["vragen"], key=lambda x: x["number"]) if v.get("uitwerkbijlage")]
    if ub:
        L += ["## Uitwerkbijlage", ""]
        for v in ub:
            u = v["uitwerkbijlage"]
            L += [f"### Bij vraag {v['number']}", ""]
            if u.get("rows"):
                L += md_table(u["rows"]) + [""]
            if u.get("figure_id"):
                L += [f"![uitwerkbijlage](../figures/{u['figure_id']}.png)", ""]
            if u.get("text"):
                L += [u["text"], ""]
    return "\n".join(L)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    run = ToetsRun(R)
    order = [o["opgave_id"] for o in run.blueprint()["opgaven"]]
    only = opt(argv, "--opgave")
    (R / "34_student").mkdir(exist_ok=True)
    for oid, it in run.items(only).items():
        n = order.index(oid) + 1 if oid in order else int(oid.lstrip("O"))
        (R / "34_student" / f"{oid}.md").write_text(build(R, it, n), encoding="utf-8")
        print(f"[student_build] 34_student/{oid}.md ({len(it['vragen'])} vragen)")


if __name__ == "__main__":
    main(sys.argv)
