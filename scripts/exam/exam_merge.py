#!/usr/bin/env python3
"""E4 — merge exam judgements A/B (+R) into one record per scorepunt (specs/22 §4–§5).

Usage: exam_merge.py <run_dir>

Reads run.json, 20_criteria.json, 21_exam_units.json (+ text/), 23_judgements.<A|B|R>/<opgave>.json and
the subject's effective verb table. Writes 24_mappings.json (one record per scorepunt, linked or not) and
24_findings.json.
"""
from __future__ import annotations

import glob
import sys
from collections import Counter
from pathlib import Path

from ecommon import (CONF, Report, Units, bloom_rank, computed, criteria_index, load_bloom_rules, load_json,
                     quote_valid, save_json, validate_schema, verb_levels)


def load_judge(run_dir: Path, j: str) -> dict[str, dict]:
    items: dict[str, dict] = {}
    for f in sorted(glob.glob(str(run_dir / f"23_judgements.{j}" / "*.json"))):
        d = load_json(f)
        errs = validate_schema(d, "exam_judgements.schema.json")
        if errs:
            sys.exit(f"invalid exam judgement file {f}: {errs[0]}")
        for it in d["items"]:
            items[it["scorepunt_id"]] = it
    return items


def merged_bloom(rules: dict, js: dict) -> tuple[str, str | None]:
    """Agreed level, else the one its verb has in the table, else the lower one (specs/12 §6.2)."""
    blooms = {js[j]["bloom"] for j in js}
    if len(blooms) == 1:
        return blooms.pop(), None
    by_table = [js[j]["bloom"] for j in js if js[j]["bloom"] in verb_levels(rules, js[j].get("bloom_verb"))]
    bloom = by_table[0] if len(set(by_table)) == 1 else min((js[j]["bloom"] for j in js), key=bloom_rank)
    return bloom, f"bloom A: {js['A']['bloom']} / B: {js['B']['bloom']}"


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("exam_merge")
    run = load_json(run_dir / "run.json")
    rules = load_bloom_rules(run["subject"])
    units = Units(run_dir)
    crit = criteria_index(load_json(run_dir / "20_criteria.json"))

    J = {j: load_judge(run_dir, j) for j in ("A", "B")}
    R = load_judge(run_dir, "R")
    sp_ids = [sp["unit_id"] for sp in units.scorepunten]
    for j in J:
        missing = [s for s in sp_ids if s not in J[j]]
        if missing:
            rep.fail("ES1", f"judge {j} has no item for {len(missing)} scorepunten, e.g. {missing[:3]}")
    for j, items in list(J.items()) + [("R", R)]:
        for sid, it in items.items():
            if sid not in units.by_id:
                rep.fail("ES1", f"judge {j}: unknown scorepunt {sid}")
            for c in [it.get("criterion_id")] + it.get("also_touches", []):
                if c and c not in crit:
                    rep.fail("EC1", f"judge {j} {sid}: unknown criterion {c}")
    if rep.failed:
        rep.print_and_exit()

    links, findings = [], []
    for sp in units.scorepunten:
        sid, q = sp["unit_id"], units.by_id[sp["question_id"]]
        qtext = units.question_text(q["unit_id"])
        tol = units.tolerant(sp["exam_id"])
        js = {"A": J["A"][sid], "B": J["B"][sid]}
        repaired = None
        if sid in R:
            r = R[sid]
            ca, cb = js["A"].get("criterion_id"), js["B"].get("criterion_id")
            repaired = "A" if ca != r.get("criterion_id") and cb == r.get("criterion_id") else "B"
            js[repaired] = r
        crits = {j: js[j].get("criterion_id") for j in js}
        valid = {j: bool(crits[j]) and quote_valid(js[j].get("quote"), qtext, tol) for j in js}
        judges = {j: {"criterion_id": crits[j], "bloom": js[j].get("bloom"), "quote_valid": valid[j],
                      "repaired": repaired == j} for j in js}
        base = {"scorepunt_id": sid, "question_id": q["unit_id"], "opgave_id": q["opgave_id"],
                "exam_id": sp["exam_id"], "points": sp["points"], "judges": judges, "verifier": None,
                "status": "proposed"}
        # R decides: R without criterion leaves the scorepunt unlinked whatever the other judge said
        linking = [] if repaired and not crits[repaired] else [j for j in js if crits[j]]
        if not linking or not any(valid[j] for j in linking):
            reason = "no_criterion" if not linking else "invalid_quote"
            links.append({**base, "criterion_id": None, "group_id": None, "alt_criterion": None, "bloom": None,
                          "bloom_verb": None, "quote": None, "also_touches": [], "answer_checked": False,
                          "confidence": None, "confidence_judged": None, "unlinked_reason": reason,
                          "note": "; ".join(x for x in (js["A"].get("note"), js["B"].get("note")) if x) or None})
            findings.append({"finding": "buiten huidige syllabus" if reason == "no_criterion" else "citaat ongeldig",
                             "scorepunt_id": sid, "criterion_id": None, "points": sp["points"],
                             "note": links[-1]["note"]})
            continue
        notes: list[str] = []
        if crits["A"] and crits["A"] == crits["B"]:
            primary = repaired or ("A" if valid["A"] else "B")
            bloom, bnote = merged_bloom(rules, js)
            if bnote:
                notes.append(bnote)
            conf = "high" if bnote is None and all(valid.values()) else "medium"
            alt = None
        else:
            primary = repaired if repaired and crits[repaired] and valid[repaired] else \
                next(j for j in ("A", "B") if crits[j] and valid[j])
            other = "B" if primary == "A" else "A"
            bloom, conf, alt = js[primary]["bloom"], "low", crits[other]
            notes.append(f"{other}: {crits[other] or 'geen criterium'}")
        jd = js[primary]
        if repaired:
            bloom = js[repaired]["bloom"]
        verb = jd.get("bloom_verb")
        lv = verb_levels(rules, verb)
        if not lv and not repaired and computed(sp["text"], qtext) and bloom_rank(bloom) < bloom_rank("toepassen"):
            notes.append(f"antwoord is een berekening: {bloom} → toepassen")
            bloom = "toepassen"
        if lv and bloom not in lv:
            notes.append(f"werkwoord '{verb}' = {'/'.join(lv)} volgens tabel")
            conf = min(conf, "medium", key=CONF.index)
        cid = crits[primary]
        touches = sorted({c for j in js for c in js[j].get("also_touches", []) if c and c != cid})
        links.append({**base, "criterion_id": cid, "group_id": crit[cid]["group_id"], "alt_criterion": alt,
                      "bloom": bloom, "bloom_verb": verb, "quote": jd["quote"], "also_touches": touches,
                      "answer_checked": bool(jd.get("answer_checked")), "confidence": conf,
                      "confidence_judged": conf, "unlinked_reason": None, "note": "; ".join(notes) or None})
        cb = crit[cid]["bloom"]
        if bloom_rank(bloom) > bloom_rank(cb):
            findings.append({"finding": "examen boven criterium", "scorepunt_id": sid, "criterion_id": cid,
                             "points": sp["points"], "note": f"examen {bloom}, criterium {cb}"})
        elif bloom_rank(bloom) < bloom_rank(cb):
            findings.append({"finding": "examen onder criterium", "scorepunt_id": sid, "criterion_id": cid,
                             "points": sp["points"], "note": f"examen {bloom}, criterium {cb}"})

    out = {"links": links, "findings": findings}
    for e in validate_schema(out, "exam_mappings.schema.json")[:5]:
        rep.fail("ES1", e)
    save_json(run_dir / "24_mappings.json", out)
    save_json(run_dir / "24_findings.json", {"findings": findings})
    linked = [l for l in links if l["criterion_id"]]
    for eid, ex in units.exams.items():
        lp = sum(l["points"] for l in linked if l["exam_id"] == eid)
        up = sum(l["points"] for l in links if l["exam_id"] == eid and not l["criterion_id"])
        rep.info("E4", f"{eid}: {lp} points linked, {up} unlinked (max {ex['max_score']})")
    rep.info("E4", f"{len(linked)}/{len(links)} scorepunten linked; confidence {dict(Counter(l['confidence'] for l in linked))}; "
                   f"bloom {dict(Counter(l['bloom'] for l in linked))}; findings {dict(Counter(f['finding'] for f in findings))}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
