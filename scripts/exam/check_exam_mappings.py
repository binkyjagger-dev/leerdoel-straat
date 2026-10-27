#!/usr/bin/env python3
"""Deterministic checks on 24_mappings.json (specs/24 §1) and verdict application.

Usage: check_exam_mappings.py <run_dir> [--verification 25_verification.json]

Checks ES1, EQ1, EP1–EP3, EC1, EC2, MB1, MB2. With --verification the verifier's verdicts are written into
24_mappings.json. Idempotent: confidence is recomputed from `confidence_judged` each time; a dispute the repair
judge already settled the verifier's way is recorded as `resolved`.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

from ecommon import (BLOOM_ORDER, CONF, Report, Units, criteria_index, load_bloom_rules, load_json, quote_valid,
                     save_json, validate_schema, verb_in_text, verb_levels)


def expected_confidence(l: dict, lv: list[str]) -> str:
    js = l["judges"]
    a, b = js.get("A") or {}, js.get("B") or {}
    if a.get("criterion_id") and a.get("criterion_id") == b.get("criterion_id"):
        exp = "high" if a.get("bloom") == b.get("bloom") and a.get("quote_valid") and b.get("quote_valid") else "medium"
    else:
        exp = "low"
    if lv and l["bloom"] not in lv:
        exp = min(exp, "medium", key=CONF.index)
    return exp


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("check_exam_mappings")
    run = load_json(run_dir / "run.json")
    rules = load_bloom_rules(run["subject"])
    units = Units(run_dir)
    crit = criteria_index(load_json(run_dir / "20_criteria.json"))
    for name, schema in (("21_exam_units.json", "exam_units.schema.json"),
                         ("22_candidates.json", "exam_candidates.schema.json"),
                         ("24_mappings.json", "exam_mappings.schema.json")):
        if (run_dir / name).exists():
            for e in validate_schema(load_json(run_dir / name), schema)[:5]:
                rep.fail("ES1", f"{name}: {e}")
    data = load_json(run_dir / "24_mappings.json")
    links = data["links"]

    # EP1: every scorepunt exactly once
    count = Counter(l["scorepunt_id"] for l in links)
    for sp in units.scorepunten:
        if count.get(sp["unit_id"], 0) != 1:
            rep.fail("EP1", f"{sp['unit_id']}: {count.get(sp['unit_id'], 0)} records in 24_mappings.json")
    for sid in set(count) - {sp["unit_id"] for sp in units.scorepunten}:
        rep.fail("EP1", f"{sid}: not a scorepunt of the exam units")

    per_exam = defaultdict(int)
    for l in links:
        sp = units.by_id.get(l["scorepunt_id"])
        if not sp:
            continue
        per_exam[l["exam_id"]] += l["points"]
        # EP3
        if l["points"] != sp["points"]:
            rep.fail("EP3", f"{l['scorepunt_id']}: points {l['points']} != scorepunt {sp['points']}")
        cid = l["criterion_id"]
        if not cid:
            continue
        tag = f"{l['scorepunt_id']} x {cid}"
        # EC1
        if cid not in crit:
            rep.fail("EC1", f"{tag}: unknown criterion")
        for c in l["also_touches"]:
            if c not in crit or c == cid:
                rep.fail("EC1", f"{tag}: also_touches {c} unknown or the linked criterion")
        # EQ1
        qtext = units.question_text(l["question_id"])
        if not quote_valid(l["quote"], qtext, units.tolerant(l["exam_id"])):
            rep.fail("EQ1", f"{tag}: quote not verbatim in the question text or too long")
        # MB1
        if l["bloom"] not in BLOOM_ORDER:
            rep.fail("MB1", f"{tag}: bloom {l['bloom']} not a level")
        lv = verb_levels(rules, l.get("bloom_verb"))
        if lv and l["bloom"] not in lv and "volgens tabel" not in (l.get("note") or ""):
            rep.fail("MB1", f"{tag}: verb '{l['bloom_verb']}' is {lv} but bloom {l['bloom']} without note")
        # MB2
        if l.get("bloom_verb") and not verb_in_text(l["bloom_verb"], qtext):
            rep.warn("MB2", f"{tag}: bloom_verb '{l['bloom_verb']}' not found in the question")
        # EC2
        exp = expected_confidence(l, lv)
        if l["confidence_judged"] != exp:
            rep.fail("EC2", f"{tag}: confidence_judged {l['confidence_judged']} != computed {exp}")

    # EP2
    for eid, ex in units.exams.items():
        if per_exam[eid] != ex["max_score"]:
            rep.fail("EP2", f"{eid}: linked + unlinked points = {per_exam[eid]}, max_score {ex['max_score']}")

    if "--verification" in argv:
        ver = load_json(run_dir / argv[argv.index("--verification") + 1])
        for e in validate_schema(ver, "exam_verification.schema.json"):
            rep.fail("ES1", f"verification: {e}")
        idx = {l["scorepunt_id"]: l for l in links}
        for l in links:
            l["confidence"], l["verifier"] = l["confidence_judged"], None
        applied, resolved = 0, 0
        for v in ver["links"]:
            l = idx.get(v["scorepunt_id"])
            if not l or l["criterion_id"] != v["criterion_id"]:
                # the repair judge changed or removed the link: a dispute is settled, a pass is worth a look
                if v["verdict"] == "dispute":
                    resolved += 1
                else:
                    rep.warn("ES1", f"{v['scorepunt_id']} x {v['criterion_id']} passed by the verifier was changed in repair")
                continue
            verdict = v["verdict"]
            repaired = any(j and j.get("repaired") for j in l["judges"].values())
            if verdict == "dispute" and repaired and v.get("bloom_should_be") in (None, l["bloom"]) \
                    and v.get("criterion_should_be") in (None, l["criterion_id"]):
                verdict = "resolved"
                resolved += 1
            l["verifier"] = verdict + (f": {v['reason']}" if v.get("reason") else "")
            adj = v.get("confidence_adjust")
            if adj and l["confidence"]:
                i = CONF.index(l["confidence"])
                l["confidence"] = CONF[min(2, i + 1)] if adj == "up" else CONF[max(0, i - 1)]
            applied += 1
        save_json(run_dir / "24_mappings.json", data)
        rep.info("ES1", f"applied {applied} verdicts ({resolved} resolved by repair); "
                        f"{len(ver['missing_links'])} missing-link proposals")

    linked = [l for l in links if l["criterion_id"]]
    rep.info("EP2", f"{len(linked)}/{len(links)} scorepunten linked; bloom {dict(Counter(l['bloom'] for l in linked))}; "
                    f"confidence {dict(Counter(l['confidence'] for l in linked))}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
