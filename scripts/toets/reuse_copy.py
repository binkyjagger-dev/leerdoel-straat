#!/usr/bin/env python3
"""T3 — copy reused opgaven verbatim from the toetsbank into the run (specs/32 §1 `reuse`, specs/35 §4).

Usage: reuse_copy.py <run_dir> [--toetsbank <dir>] [--subjects <dir>]

For every opgave of 32_blueprint.json with `reused_from` (the planner copied it there from the toetsbank record):
writes 33_items/<opgave>.json from toetsen/<toets_id>.json — intro, data, sources, figures, stems and cv verbatim —
with the vraag ids and numbers of this toets (`builds_on_vragen` renumbered). Its stored merged labels are written as
34_labels.A/ and 34_labels.B/<opgave>.json (identical, so label_merge.py --toets takes them as agreed), because the
labels of a reused opgave count in the realised shares and it is not labelled, solved or verified again.
Warns when a stem names "vraag n" with an old number that changed, or when a figure id is also used by another
opgave of the run (both need the teacher's eye, docs/bouwvragen-toets.md Fase 3). Fails when the reused opgave in the
blueprint does not match the toetsbank record (vragen, points, criteria).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from tcommon import LABEL_FIELDS, Report, load_json, save_json
from toetsrun import ToetsRun, opt, subjects_opt


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    rep = Report("reuse_copy")
    run = ToetsRun(R, subjects_opt(argv))
    tb = Path(opt(argv, "--toetsbank")) if opt(argv, "--toetsbank") else run.toetsbank()
    bp = run.blueprint()
    other_figs = {f["figure_id"]: oid for oid, it in run.items().items() for f in it["figures"]}
    n = 0
    for og in bp["opgaven"]:
        rf = og.get("reused_from")
        if not rf:
            continue
        tf = tb / "toetsen" / f"{rf['toets_id']}.json"
        src = next((o for o in load_json(tf)["opgaven"] if o["opgave_id"] == rf["opgave_id"]), None) if tf.exists() else None
        if not src:
            rep.fail("RU", f"{og['opgave_id']}: {rf['toets_id']}/{rf['opgave_id']} not in the toetsbank")
            continue
        old, new = sorted(src["vragen"], key=lambda v: v["number"]), sorted(og["vragen"], key=lambda v: v["number"])
        if [(v["points"], [s["criterion_id"] for s in v["scorepunten"]]) for v in old] != \
                [(v["points"], [s["criterion_id"] for s in v["scorepunten"]]) for v in new]:
            rep.fail("RU", f"{og['opgave_id']}: the blueprint's vragen differ from the toetsbank record")
            continue
        renum = {o["number"]: v["number"] for o, v in zip(old, new)}
        vragen, labels = [], []
        for o, v in zip(old, new):
            item = {k: o[k] for k in ("stem", "uitwerkbijlage", "cv", "new_concepts") if k in o}
            item.update(vraag_id=v["vraag_id"], number=v["number"], points=o["points"],
                        builds_on_vragen=[renum.get(x, x) for x in o.get("builds_on_vragen", [])])
            vragen.append(item)
            if o["number"] != v["number"]:
                for m in re.finditer(r"\bvraag\s+(\d+)", o["stem"], re.I):
                    if int(m.group(1)) in renum and renum[int(m.group(1))] != int(m.group(1)):
                        rep.warn("RU", f"{v['vraag_id']}: the stem says 'vraag {m.group(1)}', which is vraag "
                                       f"{renum[int(m.group(1))]} in this toets (verbatim copy: check with the teacher)")
            lab = o.get("label")
            if lab:
                labels.append({**{f: lab.get(f) for f in LABEL_FIELDS}, "question_id": v["vraag_id"], "question_number": v["number"],
                               "proposed_pattern": None, "builds_on_questions": [renum.get(x, x) for x in lab.get("builds_on_questions", [])],
                               "example_quality": None, "example_quality_reason": None, "evidence": {},
                               "note": f"overgenomen uit de toetsbank ({rf['toets_id']}/{rf['opgave_id']})"})
            else:
                rep.warn("RU", f"{v['vraag_id']}: the toetsbank record has no labels; label this opgave in T4")
        for f in src.get("figures", []):
            if f["figure_id"] in other_figs and other_figs[f["figure_id"]] != og["opgave_id"]:
                rep.warn("RU", f"{og['opgave_id']}: figure id {f['figure_id']} is also used by {other_figs[f['figure_id']]}")
        save_json(R / "33_items" / f"{og['opgave_id']}.json",
                  {"opgave_id": og["opgave_id"], "title": src["title"], "intro": src["intro"], "data": src["data"],
                   "sources": src["sources"], "figures": src.get("figures", []), "vragen": vragen,
                   "writer_notes": f"hergebruikt uit {rf['toets_id']}/{rf['opgave_id']}"})
        if labels and len(labels) == len(vragen):
            for letter in ("A", "B"):
                save_json(R / f"34_labels.{letter}" / f"{og['opgave_id']}.json",
                          {"labeller": letter, "mode": "toets", "opgave_id": og["opgave_id"], "items": labels})
        n += 1
        rep.info("RU", f"{og['opgave_id']} ← {rf['toets_id']}/{rf['opgave_id']}: {len(vragen)} vragen copied verbatim")
    if not n and not rep.failed:
        rep.info("RU", "no reused opgaven in the blueprint")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
