#!/usr/bin/env python3
"""Bloom rules G3–G6 (specs/02 §2, specs/04 §2).

Usage: bloom_check.py <groups.json> [<02_plan.json>] [--write] [--subject <slug>]

  The verb table is the *effective* one (specs/02 §2 rule 6): data/bloom_verbs_nl.json with the
  subject's subjects/<slug>/bloom_verbs.json applied per verb. --subject names the subject; without it
  the script reads `subject` from the nearest run.json; without either the generic table is used.

  G3  criterion bloom_verb is in the effective verb list for its level (ambiguous verbs: level allowed)
  G4  criterion text_expert does not use a forbidden (non-observable) verb
  G5  goal.bloom = max(criteria.bloom)  — computed; with --write the file is updated in place
  G6  goal.bloom <= target_bloom_max + 1  (warning; the verifier judges it)
"""
from __future__ import annotations

import re
import sys

from common import BLOOM_ORDER, Report, bloom_rank, load_bloom_rules, load_json, save_json, stem_verb as _stem, subject_for


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    write = "--write" in argv
    subject = argv[argv.index("--subject") + 1] if "--subject" in argv else None
    args = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and argv[i - 1] != "--subject"]
    groups_path = args[0]
    plan = load_json(args[1]) if len(args) > 1 else None

    subject = subject or subject_for(groups_path)
    rules = load_bloom_rules(subject)
    verbs = {lvl: {_stem(v) for v in vs} for lvl, vs in rules["verbs"].items()}
    ambiguous = {k.lower(): set(v) for k, v in rules["ambiguous"].items()}
    forbidden = [f.lower() for f in rules["forbidden_criterion_verbs"]]
    targets = {p["unit_id"]: p["target_bloom_max"] for p in plan["units"]} if plan else {}

    rep = Report("bloom_check")
    eff = rules["_effective"]
    if eff["overlay"]:
        n = sum(1 for o in eff["overrides"] if o["changed"])
        rep.info("G3", f"verb table: generic + {eff['overlay']} ({n} verbs reclassified; decision {eff['decision']})")
    else:
        rep.info("G3", f"verb table: generic only (subject: {subject or 'unknown'})")
    data = load_json(groups_path)
    changed = False
    for g in data["groups"]:
        gid = g["group_id"]
        levels = []
        for c in g["criteria"]:
            cid, lvl, verb = c["criterion_id"], c["bloom"], _stem(c["bloom_verb"])
            levels.append(lvl)
            allowed = lvl in verbs and verb in verbs[lvl]
            if not allowed and verb in ambiguous:
                allowed = lvl in ambiguous[verb]
            if not allowed:
                rep.fail("G3", f"{cid}: verb '{verb}' not listed for level '{lvl}'")
            text = c["text_expert"].lower()
            for f in forbidden:
                if re.search(rf"\b{re.escape(f)}\b", text):
                    rep.fail("G4", f"{cid}: forbidden verb '{f}' in criterion")
        computed = max(levels, key=bloom_rank)
        if g["goal"].get("bloom") != computed:
            rep.info("G5", f"{gid}: goal.bloom set to '{computed}' (was {g['goal'].get('bloom')!r})")
            g["goal"]["bloom"] = computed
            changed = True
        tgt = targets.get(g["unit_id"])
        if tgt and bloom_rank(computed) > bloom_rank(tgt) + 1:
            rep.warn("G6", f"{gid}: goal bloom '{computed}' exceeds target '{tgt}' by more than one level")
    dist = {lvl: 0 for lvl in BLOOM_ORDER}
    for g in data["groups"]:
        for c in g["criteria"]:
            dist[c["bloom"]] += 1
    rep.info("G5", f"criterion bloom distribution: {dist}")
    if changed and write:
        save_json(groups_path, data)
        rep.info("G5", f"wrote computed goal.bloom to {groups_path}")
    elif changed:
        rep.warn("G5", "goal.bloom differs from computed value; rerun with --write to fix")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
