#!/usr/bin/env python3
"""Toets-straat validators (specs/34).

Usage:
  validate_toets.py order <order.json> [--draft] [--run <R>] [--bank <dir>] [--toetsbank <dir>] [--subjects <dir>]
                          [--ask-out <file>] [--json-out <file>]
  validate_toets.py blueprint <R>        schema of 32_blueprint.json (+ 32_blueprint_review.json); content: blueprint_check.py
  validate_toets.py items <R> [--opgave <id>]   schema of 33_items/<opgave>.json, one file per blueprint opgave; content: items_check.py
  validate_toets.py verification <R> [--file <35_verification….json>]
                                         schema; one verdict per vraag of the blueprint (or of `only`); a repair verdict
                                         has a finding; a pass verdict has no `must` finding; finding vraag ids belong to
                                         the vraag; proposed decisions have question/proposed/impact/applies_to

order — checks O1–O6 of specs/34 §1 on the teacher's toetsopdracht.json (--draft) or the confirmed R/31_order.json.
  O1 schema toets_order; without --draft also complete: title, level, n_opgaven, n_vragen, the bloom_mix key and
     every settable knob present and not null (specs/32 §1: no implicit default)
  O2 every matrix group_id exists in the criteria, no group twice; criteria_include/exclude ids exist; the order's
     subject and criteria_run match the run / exam bank
  O3 each knob is "vrij" or a share map over valid values summing to 1 (± 0.001); pattern codes are active catalogue
     codes; computed knobs (combination) are not set; bloom_mix likewise, without creëren
  O4 n_vragen ≥ n_opgaven; n_vragen ≤ total points
  O5 reuse entries exist in the toetsbank and belong to the same criteria run; their points per group do not exceed
     the matrix (warnings are not errors)
  O6 feasibility warnings: a Bloom level with points but no criterion in the matrix that allows it (criterion
     Bloom + 1); route/schema shares while the pattern shares hold no pattern of an applicable kind; a group whose
     criteria are all excluded
With --draft, missing or null fields are not errors but questions for the dialogue (T1, specs/32 §3): they are
printed as ASK lines and, with --ask-out, written as JSON with the reference shares per knob.
Inputs: criteria, knobs, catalogue and reference from <R> (30_criteria.json, 30_knobs.json, 30_patterns.json,
30_reference_profile.json, run.json) when the order lies in a run folder or --run is given; else from the subject's
exam bank (criteria.json, register.json, profiel/) and the catalogue files. Toetsbank default
subjects/<s>/toetsbank.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from tcommon import (clean_reference, MIX_LEVELS, ROOT, SHARE_EPS, BLOOM_ORDER, Report, bloom_rank, kinds_of, knob_index, load_json,
                     load_knobs, merged_catalogue, pattern_index, save_json, validate_schema)

REQUIRED = ["title", "level", "n_opgaven", "n_vragen"]


def opt(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None


def criteria_index(groups_doc: dict) -> tuple[dict, dict]:
    groups, crit = {}, {}
    for g in groups_doc["groups"]:
        groups[g["group_id"]] = g
        for c in g["criteria"]:
            crit[c["criterion_id"]] = {**c, "group_id": g["group_id"]}
    return groups, crit


def reference_profile(run: Path | None, bank: Path, subjects: Path, subject: str) -> dict | None:
    for p in ([run / "30_reference_profile.json"] if run else []) + [bank / "profiel" / "referentieprofiel.json",
                                                                       subjects / subject / "toets" / "seed_profile.json"]:
        if p.exists():
            return clean_reference(load_json(p), knob_index(load_knobs()))
    return None


def check_order(argv: list[str]) -> None:
    rep = Report("validate_toets order")
    path = Path(argv[2])
    draft = "--draft" in argv
    order = load_json(path)
    subjects = Path(opt(argv, "--subjects")) if opt(argv, "--subjects") else ROOT / "subjects"
    run = Path(opt(argv, "--run")) if opt(argv, "--run") else (path.parent if (path.parent / "30_criteria.json").exists() else None)
    subject = order.get("subject") or ""
    bank = Path(opt(argv, "--bank")) if opt(argv, "--bank") else subjects / subject / "examenbank"
    tbank = Path(opt(argv, "--toetsbank")) if opt(argv, "--toetsbank") else subjects / subject / "toetsbank"

    # O1 schema (+ completeness)
    for e in validate_schema(order, "toets_order.schema.json"):
        rep.fail("O1", e)
    if rep.failed:
        rep.print_and_exit(opt(argv, "--json-out"))
    knobs = knob_index(load_json(run / "30_knobs.json") if run and (run / "30_knobs.json").exists() else load_knobs())
    cat = load_json(run / "30_patterns.json") if run and (run / "30_patterns.json").exists() else merged_catalogue(subject, subjects=subjects)
    pidx = pattern_index(cat)
    ask = []
    for f in REQUIRED:
        if order.get(f) is None:
            ask.append({"field": f})
    if "bloom_mix" not in order:
        ask.append({"field": "bloom_mix"})
    settable = [k for k, d in knobs.items() if d["settable"]]
    for k in settable:
        if (order.get("knobs") or {}).get(k) is None:
            ask.append({"field": f"knobs.{k}"})
    for a in ask:
        (rep.info if draft else rep.fail)("ASK" if draft else "O1", f"{a['field']}: missing or null"
                                          + (" — ask in the dialogue" if draft else " (the confirmed order must be complete)"))

    # O2 criteria
    if run and (run / "30_criteria.json").exists():
        groups_doc, cr_src = load_json(run / "30_criteria.json"), f"{run.name}/30_criteria.json"
        expected_run = load_json(run / "run.json").get("criteria_run") if (run / "run.json").exists() else None
        run_subject = load_json(run / "run.json").get("subject") if (run / "run.json").exists() else subject
    elif (bank / "criteria.json").exists():
        groups_doc, cr_src = load_json(bank / "criteria.json"), f"{bank}/criteria.json"
        expected_run = load_json(bank / "register.json")["criteria_run"] if (bank / "register.json").exists() else None
        run_subject = subject
    else:
        rep.fail("O2", f"no criteria: neither a run folder with 30_criteria.json nor an exam bank at {bank}")
        rep.print_and_exit(opt(argv, "--json-out"))
    groups, crit = criteria_index(groups_doc)
    if run_subject != subject:
        rep.fail("O2", f"order subject '{subject}' != run subject '{run_subject}'")
    if expected_run and order["criteria_run"] != expected_run:
        rep.fail("O2", f"criteria_run '{order['criteria_run']}' != the criteria version '{expected_run}' ({cr_src})")
    matrix = {}
    for row in order["matrix"]:
        g = row["group_id"]
        if g in matrix:
            rep.fail("O2", f"group {g} appears twice in the matrix")
        matrix[g] = matrix.get(g, 0) + row["points"]
        if g not in groups:
            rep.fail("O2", f"matrix group {g} not in {cr_src}")
    for key in ("criteria_include", "criteria_exclude"):
        for c in order.get(key) or []:
            if c not in crit:
                rep.fail("O2", f"{key}: criterion {c} not in {cr_src}")
    if not matrix and not draft:
        rep.fail("O2", "the matrix is empty")
    total = sum(matrix.values())

    # O3 knobs and bloom mix
    for k, v in (order.get("knobs") or {}).items():
        if k not in knobs:
            rep.fail("O3", f"knobs.{k}: not a knob")
            continue
        if not knobs[k]["settable"]:
            rep.fail("O3", f"knobs.{k}: computed knob, cannot be set")
            continue
        if v is None or v == "vrij":
            continue
        valid = [c for c, p in pidx.items() if p.get("status") == "active"] if knobs[k]["values"] == "catalogue" else knobs[k]["values"]
        for val, share in v.items():
            if val not in valid:
                extra = " (retired)" if k == "pattern" and val in pidx else ""
                rep.fail("O3", f"knobs.{k}: value '{val}' not allowed{extra}; allowed: {', '.join(valid)}")
        if abs(sum(v.values()) - 1.0) > SHARE_EPS:
            rep.fail("O3", f"knobs.{k}: shares sum to {sum(v.values()):.3f}, not 1")
    bm = order.get("bloom_mix")
    if bm:
        for lvl in bm:
            if lvl not in MIX_LEVELS:
                rep.fail("O3", f"bloom_mix: level '{lvl}' not allowed (creëren has no pattern)")
        if abs(sum(bm.values()) - 1.0) > SHARE_EPS:
            rep.fail("O3", f"bloom_mix: shares sum to {sum(bm.values()):.3f}, not 1")

    # O4 counts
    no, nv = order.get("n_opgaven"), order.get("n_vragen")
    if no is not None and nv is not None and nv < no:
        rep.fail("O4", f"n_vragen {nv} < n_opgaven {no}")
    if nv is not None and total and nv > total:
        rep.fail("O4", f"n_vragen {nv} > total points {total}")

    # O5 reuse
    reuse = order.get("reuse") or []
    if reuse:
        reg = load_json(tbank / "register.json") if (tbank / "register.json").exists() else None
        if reg is None:
            rep.fail("O5", f"reuse given but no toetsbank at {tbank}")
        else:
            for e in validate_schema(reg, "toetsbank.schema.json")[:3]:
                rep.fail("O5", f"toetsbank register: {e}")
            known = {t["toets_id"] for t in reg["toetsen"]}
            per_group, seen = defaultdict(int), set()
            for r in reuse:
                tag = f"reuse {r['toets_id']}/{r['opgave_id']}"
                if (r["toets_id"], r["opgave_id"]) in seen:
                    rep.fail("O5", f"{tag}: listed twice")
                seen.add((r["toets_id"], r["opgave_id"]))
                tf = tbank / "toetsen" / f"{r['toets_id']}.json"
                if r["toets_id"] not in known or not tf.exists():
                    rep.fail("O5", f"{tag}: toets not in the toetsbank")
                    continue
                t = load_json(tf)
                if t["criteria_run"] != order["criteria_run"] or reg["criteria_run"] != order["criteria_run"]:
                    rep.fail("O5", f"{tag}: toets belongs to criteria run {t['criteria_run']}, the order to {order['criteria_run']}")
                og = next((o for o in t["opgaven"] if o["opgave_id"] == r["opgave_id"]), None)
                if not og:
                    rep.fail("O5", f"{tag}: opgave not in the toets")
                    continue
                for v in og["vragen"]:
                    for s in v["scorepunten"]:
                        per_group[s.get("group_id") or (crit.get(s["criterion_id"]) or {}).get("group_id")] += s["points"]
            for g, p in sorted(per_group.items(), key=lambda kv: str(kv[0])):
                if p > matrix.get(g, 0):
                    rep.fail("O5", f"reused opgaven hold {p} points of {g}, the matrix gives {matrix.get(g, 0)}")
                else:
                    rep.info("O5", f"reused opgaven hold {p} of {matrix[g]} points of {g}")

    # O6 feasibility warnings
    incl = set(order.get("criteria_include") or []) or None
    excl = set(order.get("criteria_exclude") or [])
    usable = [c for c in crit.values() if c["group_id"] in matrix and c["criterion_id"] not in excl
              and (incl is None or c["criterion_id"] in incl)]
    for g in matrix:
        if g in groups and not any(c["group_id"] == g for c in usable):
            rep.warn("O6", f"matrix group {g} has points but all its criteria are excluded")
    if bm:
        for lvl, share in bm.items():
            if share > 0 and lvl in BLOOM_ORDER and not any(bloom_rank(lvl) <= bloom_rank(c["bloom"]) + 1 for c in usable):
                rep.warn("O6", f"bloom_mix {lvl} {share:.0%}: no criterion in the matrix allows {lvl} (criterion Bloom + 1)")
    pat = (order.get("knobs") or {}).get("pattern")
    if isinstance(pat, dict):
        kinds = set().union(*(kinds_of(c, pidx) for c, s in pat.items() if s > 0)) if pat else set()
        for k in ("route", "schema"):
            if isinstance((order.get("knobs") or {}).get(k), dict):
                ak = knobs[k]["applies_to_kinds"]
                if isinstance(ak, list) and not kinds & set(ak):
                    rep.warn("O6", f"knobs.{k} has shares but the pattern shares hold no {'/'.join(ak)} pattern")
    rep.info("O1", f"order {path.name}: {len(matrix)} groups, {total} points, {no} opgaven, {nv} vragen"
                   + (f", {len(ask)} field(s) to ask" if draft else ""))
    if opt(argv, "--ask-out"):
        ref = reference_profile(run, bank, subjects, subject)
        for a in ask:
            k = a["field"].split(".", 1)[1] if a["field"].startswith("knobs.") else ("bloom" if a["field"] == "bloom_mix" else None)
            if k and ref:
                a["reference"] = None if k in ref.get("unknown_knobs", []) else {
                    v: d["share"] for v, d in (ref.get("pooled") or {}).get(k, {}).items()} or None
                a["reference_label"] = ref.get("label") or ref.get("source")
        save_json(opt(argv, "--ask-out"), {"order": str(path), "ask": ask})
    rep.print_and_exit(opt(argv, "--json-out"))


def check_blueprint(argv: list[str]) -> None:
    rep = Report("validate_toets blueprint")
    R = Path(argv[2])
    for e in validate_schema(load_json(R / "32_blueprint.json"), "blueprint.schema.json"):
        rep.fail("BP1", f"32_blueprint.json: {e}")
    if (R / "32_blueprint_review.json").exists():
        for e in validate_schema(load_json(R / "32_blueprint_review.json"), "blueprint_review.schema.json"):
            rep.fail("BP1", f"32_blueprint_review.json: {e}")
    rep.info("BP1", "schema only; run blueprint_check.py for BP1–BP10")
    rep.print_and_exit()


def check_items(argv: list[str]) -> None:
    rep = Report("validate_toets items")
    R = Path(argv[2])
    bp = load_json(R / "32_blueprint.json")
    only = opt(argv, "--opgave")
    for o in bp["opgaven"]:
        if only and o["opgave_id"] != only:
            continue
        p = R / "33_items" / f"{o['opgave_id']}.json"
        if not p.exists():
            rep.fail("IT1", f"{o['opgave_id']}: no 33_items/{p.name}")
            continue
        d = load_json(p)
        for e in validate_schema(d, "toets_items.schema.json")[:5]:
            rep.fail("IT1", f"{p.name}: {e}")
        if d.get("opgave_id") != o["opgave_id"]:
            rep.fail("IT1", f"{p.name}: opgave_id {d.get('opgave_id')}")
    rep.info("IT1", "schema only; run items_check.py, calc_check.py, figures.py and overlap_check.py per opgave")
    rep.print_and_exit()


def check_verification(argv: list[str]) -> None:
    rep = Report("validate_toets verification")
    R = Path(argv[2])
    path = Path(opt(argv, "--file")) if opt(argv, "--file") else R / "35_verification.json"
    ver = load_json(path)
    errs = validate_schema(ver, "toets_verification.schema.json")
    for e in errs[:10]:
        rep.fail("VF", f"{path.name}: {e}")
    if errs:
        rep.print_and_exit()
    bp = load_json(R / "32_blueprint.json")
    vids = [v["vraag_id"] for o in bp["opgaven"] for v in o["vragen"]
            if (not ver.get("only") or o["opgave_id"] in ver["only"]) and not o.get("reused_from")]  # reused: not re-verified
    seen = {}
    for v in ver["vragen"]:
        if v["vraag_id"] in seen:
            rep.fail("VF", f"{v['vraag_id']}: two verdicts")
        seen[v["vraag_id"]] = v
        if v["vraag_id"] not in vids:
            rep.fail("VF", f"{v['vraag_id']}: not a vraag of the blueprint (or outside `only`)")
        if v["verdict"] == "repair" and not v["findings"]:
            rep.fail("VF", f"{v['vraag_id']}: repair without findings")
        if v["verdict"] == "pass" and any(f["severity"] == "must" for f in v["findings"]):
            rep.fail("VF", f"{v['vraag_id']}: pass with a 'must' finding")
        for f in v["findings"]:
            if f.get("vraag_id") not in (None, v["vraag_id"]):
                rep.fail("VF", f"{v['vraag_id']}: finding {f['id']} names vraag {f['vraag_id']}")
            if len(f["evidence"].split()) > 25:
                rep.warn("VF", f"{v['vraag_id']}: finding {f['id']} evidence longer than 25 words")
    for vid in vids:
        if vid not in seen:
            rep.fail("VF", f"{vid}: no verdict")
    for i, d in enumerate(ver["proposed_decisions"]):
        miss = [k for k in ("question", "proposed", "impact", "applies_to") if k not in d]
        if miss:
            rep.fail("VF", f"proposed_decisions[{i}]: missing {', '.join(miss)}")
    n_rep = sum(1 for v in ver["vragen"] if v["verdict"] == "repair")
    rep.info("VF", f"{len(ver['vragen'])} verdicts, {n_rep} repair, {len(ver['toets_findings'])} toets-level findings, "
                   f"{len(ver['proposed_decisions'])} proposed decisions")
    rep.print_and_exit()


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = argv[1]
    if cmd == "order" and len(argv) >= 3:
        check_order(argv)
    elif cmd in ("blueprint", "items", "verification") and len(argv) >= 3:
        {"blueprint": check_blueprint, "items": check_items, "verification": check_verification}[cmd](argv)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
