#!/usr/bin/env python3
"""T2b — apply the teacher's blueprint review deterministically (specs/33 §3 T2b). No agent writes the changes.

Usage: blueprint_apply.py <run_dir>

Reads 32_blueprint_review.json (schema blueprint_review) and 32_blueprint.json. The current blueprint is kept as
32_blueprint.round<N>.json first. Field entries `{target: "O2" | "O2-V3", field, value, note, accept_deviation}`:
  opgave fields: context (clears context_tags: the planner then fills only the tags), title, context_tags
  vraag fields:  pattern, points, intent, knobs.<knob>, scorepunten, builds_on_vragen
An entry with accept_deviation: true is recorded in `accepted_deviations`; blueprint_check.py then reports the
BP5–BP9 failure it causes as a warning, and the deviation goes to the verantwoording.
An entry {action: "replan", note} applies nothing: exit code 3, the orchestrator relaunches the planner with the
notes. Run blueprint_check.py afterwards. Nothing is written when an entry cannot be applied.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from tcommon import LABEL_KNOBS, Report, load_json, save_json, validate_schema

OPGAVE_FIELDS = {"context", "title", "context_tags"}
VRAAG_FIELDS = {"pattern", "points", "intent", "scorepunten", "builds_on_vragen"} | {f"knobs.{k}" for k in LABEL_KNOBS}


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    rep = Report("blueprint_apply")
    review = load_json(R / "32_blueprint_review.json")
    for e in validate_schema(review, "blueprint_review.schema.json"):
        rep.fail("BA1", e)
    if rep.failed:
        rep.print_and_exit()
    replan = [e for e in review["entries"] if e.get("action") == "replan"]
    if replan:
        print("[blueprint_apply] replan requested — relaunch toets-planner with these notes:")
        for e in replan:
            print(f"  - {e.get('note') or '(geen toelichting)'}")
        sys.exit(3)
    bp = load_json(R / "32_blueprint.json")
    ogs = {o["opgave_id"]: o for o in bp["opgaven"]}
    vs = {v["vraag_id"]: v for o in bp["opgaven"] for v in o["vragen"]}
    accepted = list(bp.get("accepted_deviations") or [])
    for e in review["entries"]:
        t, f, val = e["target"], e["field"], e["value"]
        tag = f"{t} {f}"
        if t in ogs:
            if f not in OPGAVE_FIELDS:
                rep.fail("BA2", f"{tag}: '{f}' cannot be set on an opgave ({', '.join(sorted(OPGAVE_FIELDS))})")
                continue
            if ogs[t].get("reused_from"):
                rep.fail("BA2", f"{tag}: {t} is a reused opgave and stays verbatim")
                continue
            ogs[t][f] = val
            if f == "context":
                ogs[t]["context_tags"] = []
                rep.info("BA2", f"{t}: context replaced; context_tags cleared (planner fills only the tags)")
        elif t in vs:
            if f not in VRAAG_FIELDS:
                rep.fail("BA2", f"{tag}: '{f}' cannot be set on a vraag")
                continue
            if f.startswith("knobs."):
                vs[t]["knobs"][f.split(".", 1)[1]] = val
            else:
                vs[t][f] = val
        else:
            rep.fail("BA2", f"{tag}: unknown target")
            continue
        if e.get("accept_deviation"):
            accepted = [a for a in accepted if not (a["target"] == t and a["field"] == f)]
            accepted.append({"target": t, "field": f, "value": val, "note": e.get("note")})
            if t in vs:
                vs[t]["accepted_deviation"] = e.get("note") or f"{f} op verzoek van de docent"
        rep.info("BA2", f"{tag} := {val!r}" + (" (afwijking geaccepteerd)" if e.get("accept_deviation") else ""))
    if rep.failed:
        rep.print_and_exit()  # nothing written
    n = 1
    while (R / f"32_blueprint.round{n}.json").exists():
        n += 1
    shutil.copy2(R / "32_blueprint.json", R / f"32_blueprint.round{n}.json")
    bp["accepted_deviations"] = accepted
    bp["planned_shares"] = None  # recomputed by blueprint_check.py --write
    bp["review_rounds"] = n
    save_json(R / "32_blueprint.json", bp)
    rep.info("BA1", f"{len(review['entries'])} entries applied; previous blueprint kept as 32_blueprint.round{n}.json; "
                    f"run blueprint_check.py next")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
