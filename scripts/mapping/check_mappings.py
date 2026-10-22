#!/usr/bin/env python3
"""Deterministic checks MS1, MQ1, MG1–MG4, MC1 on 14_mappings.json (specs/14 §1).

Usage: check_mappings.py <run_dir> [--verification 15_verification.json]

With --verification also validates that file against its schema and applies its confidence
adjustments / verdicts into 14_mappings.json (field `verifier`), rewriting the file.
Exit 1 on any fail.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

from mcommon import MAX_QUOTE_WORDS, Report, load_json, quote_in_text, read_text, save_json, validate_schema, words

CONF = ["low", "medium", "high"]


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("check_mappings")
    method = load_json(run_dir / "11_method_units.json")
    units = {u["unit_id"]: u for u in method["units"]}
    tolerant = method["method"]["text_extraction"] in ("ocr", "mixed")
    data = load_json(run_dir / "14_mappings.json")
    for e in validate_schema(data, "mappings.schema.json"):
        rep.fail("MS1", e)
    links = data["links"]
    findings = {(f.get("criterion_id"), f.get("unit_id"), f["finding"]) for f in data.get("findings", [])}
    scope = set(load_json(run_dir / "12_candidates.json")["scope_paragraphs"])
    cand_crit = {c["criterion_id"] for c in load_json(run_dir / "12_candidates.json")["per_criterion"]}

    # MQ1
    for l in links:
        if words(l["quote"]) > MAX_QUOTE_WORDS:
            rep.fail("MQ1", f"{l['criterion_id']} x {l['unit_id']}: quote has {words(l['quote'])} words")
        ok, _ = quote_in_text(l["quote"], read_text(run_dir, units[l["unit_id"]].get("text_ref")), tolerant)
        if not ok:
            rep.fail("MQ1", f"{l['criterion_id']} x {l['unit_id']}: quote not found in paragraph text")
    # MG1 / MG2
    leert = Counter(l["criterion_id"] for l in links if l["gradation"] == "leert")
    for cid, n in leert.items():
        if n > 1:
            rep.fail("MG1", f"{cid}: {n} leert links")
    gap_crit = {f[0] for f in findings if f[2] in ("alleen geoefend", "alleen genoemd", "niet in deze methode")}
    for cid in cand_crit:
        if leert.get(cid, 0) == 0 and cid not in gap_crit:
            rep.fail("MG1", f"{cid}: no leert and not in gap findings")
    for l in links:
        if l["treatment"] == "mentions" and l["gradation"] != "noemt":
            rep.fail("MG2", f"{l['criterion_id']} x {l['unit_id']}: mentions graded {l['gradation']}")
    # MG3
    linked = {l["unit_id"] for l in links if l["gradation"] != "noemt"}
    outside = {f[1] for f in findings if f[2].startswith("buiten syllabus")}
    for uid in scope:
        if uid not in linked and uid not in outside:
            rep.fail("MG3", f"{uid}: no link and not listed as buiten syllabus")
    # MG4
    seen = defaultdict(set)
    for l in links:
        seen[l["quote"].strip().lower()].add(l["group_id"])
    for q, gs in seen.items():
        if len(gs) > 1:
            rep.warn("MG4", f"same quote on groups {sorted(gs)}")
    # MC1 (recompute confidence from judges)
    for l in links:
        tr = {j: v["treatment"] for j, v in l["judges"].items()}
        vq = {j: v["quote_valid"] for j, v in l["judges"].items()}
        tset = set(tr.values())
        if len(tset) == 1:
            exp = "high" if all(vq.values()) else "medium"
        elif "none" in tset or "mentions" in tset:
            exp = "low"
        else:
            exp = "medium"
        if l["confidence"] != exp and not l.get("verifier"):
            rep.fail("MC1", f"{l['criterion_id']} x {l['unit_id']}: confidence {l['confidence']} != computed {exp}")

    # verification application
    if "--verification" in argv:
        vp = run_dir / argv[argv.index("--verification") + 1]
        ver = load_json(vp)
        for e in validate_schema(ver, "mapping_verification.schema.json"):
            rep.fail("MS1", f"verification: {e}")
        idx = {(l["criterion_id"], l["unit_id"]): l for l in links}
        applied = 0
        for v in ver["links"]:
            l = idx.get((v["criterion_id"], v["unit_id"]))
            if not l:
                rep.warn("MS1", f"verification verdict on unknown link {v['criterion_id']} x {v['unit_id']}")
                continue
            l["verifier"] = v["verdict"] + (f": {v['reason']}" if v.get("reason") else "")
            adj = v.get("confidence_adjust")
            if adj:
                i = CONF.index(l["confidence"])
                l["confidence"] = CONF[min(2, i + 1)] if adj == "up" else CONF[max(0, i - 1)]
            applied += 1
        save_json(run_dir / "14_mappings.json", data)
        rep.info("MS1", f"applied {applied} verifier verdicts; {len(ver['missing_links'])} missing-link proposals; {len(ver['gradation_findings'])} gradation findings")

    rep.info("MG1", f"{len(links)} links; leert for {len(leert)} criteria; {len(cand_crit)} criteria in scope; {len(scope)} paragraphs")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
