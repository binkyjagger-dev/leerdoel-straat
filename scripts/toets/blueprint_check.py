#!/usr/bin/env python3
"""T2 — checks BP1–BP10 on the planner's blueprint (specs/34 §2).

Usage: blueprint_check.py <run_dir> [--write] [--file <blueprint.json>] [--toetsbank <dir>] [--subjects <dir>]

Reads 31_order.json, 32_blueprint.json (or --file), 30_criteria.json, 30_patterns.json, 30_knobs.json,
30_context_history.json and, for reused opgaven, the toetsbank. Writes 32_blueprint.check.json. With --write
(only when nothing fails) it writes `planned_shares` (Bloom mix and knob shares by points) and the computed
`coverage` into the blueprint — the planner never writes those.

BP1  schema; opgave and vraag ids unique, vraag ids under their opgave; numbers run 1…n over the toets; seq 1…k
BP2  number of opgaven and vragen = order (a warning when an opgave has fewer than 2 or more than 5 vragen)
BP3  points per group = matrix, exact; no points outside the matrix; vraag points = sum of its scorepunten
BP4  every criterion is in a matrix group, not excluded, inside criteria_include; reused opgaven are untouched
     (equal to the toetsbank) and every order reuse entry is in the blueprint
BP5  pattern exists and is active; scorepunt Bloom in the pattern's bloom list; Bloom ≤ criterion Bloom + 1
BP6  knob values valid; applicability (route: calculation/schema, schema: schema, builds_on: not the first vraag);
     knobs_fixed binding; builds_on_vragen earlier vragen of the same opgave, non-empty exactly when builds_on = ja
BP7  Bloom mix ±5 pp, knob shares ±10 pp, with the slack rule (specs/32 §4); "vrij" knobs are not checked
BP8  no context_tags pair from the history, no avoid_contexts term, no two opgaven with the same first tag
BP9  needs_figure patterns have a planned figure; P15 is the last vraag of its opgave
BP10 coverage per group: tested and untested criteria (information)
A teacher change accepted at pause 2 (`accept_deviation` in 32_blueprint_review.json, recorded by
blueprint_apply.py in `accepted_deviations`) turns the BP5–BP9 failure it causes into a warning; BP1–BP4 are never
accepted.
"""
from __future__ import annotations

import itertools
import sys
from collections import defaultdict
from pathlib import Path

from shares import as_shares, blueprint_records, group_points, ordered_levels, point_shares, tolerance_report
from tcommon import LABEL_KNOBS, Report, bloom_rank, kinds_of, knob_applies, load_json, pattern_codes, save_json, validate_schema
from toetsrun import ToetsRun, opt, subjects_opt


class Checker:
    def __init__(self, rep: Report, accepted: list[dict]):
        self.rep, self.accepted = rep, accepted

    def fail(self, code: str, msg: str, target: str | None = None, field: str | None = None) -> None:
        if code in ("BP5", "BP6", "BP7", "BP8", "BP9"):
            for a in self.accepted:
                t_ok = target is None or a["target"] == target or target.startswith(a["target"] + "-")
                f_ok = field is None or a["field"] == field or a["field"].endswith("." + field)
                if (target or field) and t_ok and f_ok:
                    self.rep.warn(code, f"{msg} — afwijking geaccepteerd door de docent ({a['target']} {a['field']})")
                    return
        self.rep.fail(code, msg)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    rep = Report("blueprint_check")
    run = ToetsRun(R, subjects_opt(argv))
    bp_path = Path(opt(argv, "--file")) if opt(argv, "--file") else R / "32_blueprint.json"
    bp = load_json(bp_path)
    order = run.order
    errs = validate_schema(bp, "blueprint.schema.json")
    for e in errs[:10]:
        rep.fail("BP1", e)
    if errs:
        rep.print_and_exit(str(R / "32_blueprint.check.json"))
    C = Checker(rep, bp.get("accepted_deviations") or [])
    recs = blueprint_records(bp)
    vr = {r["vraag_id"]: r for r in recs}

    # BP1 ids and numbering
    oids = [o["opgave_id"] for o in bp["opgaven"]]
    if len(oids) != len(set(oids)):
        rep.fail("BP1", f"duplicate opgave ids {oids}")
    vids = [v["vraag_id"] for o in bp["opgaven"] for v in o["vragen"]]
    if len(vids) != len(set(vids)):
        rep.fail("BP1", "duplicate vraag ids")
    nums = [v["number"] for o in bp["opgaven"] for v in o["vragen"]]
    if nums != list(range(1, len(nums) + 1)):
        rep.fail("BP1", f"vraag numbers {nums} do not run 1…{len(nums)} in opgave order")
    for o in bp["opgaven"]:
        for v in o["vragen"]:
            if not v["vraag_id"].startswith(o["opgave_id"] + "-"):
                rep.fail("BP1", f"{v['vraag_id']} is not under {o['opgave_id']}")
            if [s["seq"] for s in v["scorepunten"]] != list(range(1, len(v["scorepunten"]) + 1)):
                rep.fail("BP1", f"{v['vraag_id']}: scorepunt seq does not run 1…k")

    # BP2 counts
    if len(bp["opgaven"]) != order.get("n_opgaven"):
        rep.fail("BP2", f"{len(bp['opgaven'])} opgaven, order asks {order.get('n_opgaven')}")
    if len(vids) != order.get("n_vragen"):
        rep.fail("BP2", f"{len(vids)} vragen, order asks {order.get('n_vragen')}")
    for o in bp["opgaven"]:
        if not 2 <= len(o["vragen"]) <= 5:
            rep.warn("BP2", f"{o['opgave_id']} has {len(o['vragen'])} vragen (planner guideline 2–5)")

    # BP3 points
    matrix = {m["group_id"]: m["points"] for m in order.get("matrix", [])}
    for r in recs:
        sp = sum(s["points"] for s in r["scorepunten"])
        if sp != r["points"]:
            rep.fail("BP3", f"{r['vraag_id']}: {r['points']} points but scorepunten sum to {sp}")
    gp = group_points(recs, run.crit)
    for g in sorted(set(gp) | set(matrix)):
        if gp.get(g, 0) != matrix.get(g, 0):
            rep.fail("BP3", f"group {g}: {gp.get(g, 0)} points in the blueprint, matrix {matrix.get(g, 0)}")

    # BP4 criteria and reuse
    incl = set(order.get("criteria_include") or []) or None
    excl = set(order.get("criteria_exclude") or [])
    for r in recs:
        for s in r["scorepunten"]:
            c = run.crit.get(s["criterion_id"])
            tag = f"{r['vraag_id']}-s{s['seq']}"
            if not c:
                rep.fail("BP4", f"{tag}: unknown criterion {s['criterion_id']}")
            elif c["group_id"] not in matrix:
                rep.fail("BP4", f"{tag}: {s['criterion_id']} is not in a matrix group")
            elif s["criterion_id"] in excl or (incl is not None and s["criterion_id"] not in incl):
                rep.fail("BP4", f"{tag}: {s['criterion_id']} is excluded by the order")
    tbank = Path(opt(argv, "--toetsbank")) if opt(argv, "--toetsbank") else run.toetsbank()
    wanted = {(x["toets_id"], x["opgave_id"]) for x in order.get("reuse") or []}
    got = set()
    for o in bp["opgaven"]:
        rf = o.get("reused_from")
        if not rf:
            continue
        got.add((rf["toets_id"], rf["opgave_id"]))
        tf = tbank / "toetsen" / f"{rf['toets_id']}.json"
        src = next((x for x in load_json(tf)["opgaven"] if x["opgave_id"] == rf["opgave_id"]), None) if tf.exists() else None
        if not src:
            rep.fail("BP4", f"{o['opgave_id']}: reused opgave {rf['toets_id']}/{rf['opgave_id']} not in the toetsbank")
            continue
        a = [(v["points"], [(s["points"], s["criterion_id"]) for s in v["scorepunten"]]) for v in o["vragen"]]
        b = [(v["points"], [(s["points"], s["criterion_id"]) for s in v["scorepunten"]]) for v in src["vragen"]]
        if a != b:
            rep.fail("BP4", f"{o['opgave_id']}: reused opgave differs from the toetsbank (points or criteria)")
    for miss in sorted(wanted - got):
        rep.fail("BP4", f"order reuse {miss[0]}/{miss[1]} is not in the blueprint")

    # BP5 pattern and Bloom
    for r in recs:
        codes = pattern_codes(r["pattern"])
        for c in codes:
            p = run.pidx.get(c)
            if not p:
                C.fail("BP5", f"{r['vraag_id']}: pattern {c} not in the catalogue", r["vraag_id"], "pattern")
            elif p.get("status") != "active":
                C.fail("BP5", f"{r['vraag_id']}: pattern {c} is retired", r["vraag_id"], "pattern")
        allowed = {b for c in codes if c in run.pidx for b in run.pidx[c]["bloom"]}
        for s in r["scorepunten"]:
            tag = f"{r['vraag_id']}-s{s['seq']}"
            if allowed and s["bloom"] not in allowed:
                C.fail("BP5", f"{tag}: Bloom {s['bloom']} not in pattern {r['pattern']} ({', '.join(sorted(allowed, key=bloom_rank))})",
                       r["vraag_id"], "scorepunten")
            c = run.crit.get(s["criterion_id"])
            if c and bloom_rank(s["bloom"]) > bloom_rank(c["bloom"]) + 1:
                C.fail("BP5", f"{tag}: Bloom {s['bloom']} > criterion {s['criterion_id']} ({c['bloom']}) + 1",
                       r["vraag_id"], "scorepunten")

    # BP6 knobs
    by_opgave = defaultdict(list)
    for r in recs:
        by_opgave[r["opgave_id"]].append(r)
    for r in recs:
        kinds = kinds_of(r["pattern"], run.pidx)
        for k in LABEL_KNOBS:
            kd, v = run.knobs[k], r["knobs"].get(k)
            applies = knob_applies(kd, kinds, r["first"])
            if not applies and v is not None:
                C.fail("BP6", f"{r['vraag_id']}: {k}='{v}' but the knob does not apply here (must be null)", r["vraag_id"], k)
            elif applies and v is None:
                C.fail("BP6", f"{r['vraag_id']}: {k} is null but applies here", r["vraag_id"], k)
            elif v is not None and v not in kd["values"]:
                C.fail("BP6", f"{r['vraag_id']}: {k}='{v}' not a value of {k}", r["vraag_id"], k)
        fixed = {}
        for c in pattern_codes(r["pattern"]):
            for k, val in (run.pidx.get(c) or {}).get("knobs_fixed", {}).items():
                if k in fixed and fixed[k] != val:
                    C.fail("BP6", f"{r['vraag_id']}: patterns of {r['pattern']} fix {k} differently", r["vraag_id"], k)
                fixed[k] = val
        for k, val in fixed.items():
            if k in r["knobs"] and r["knobs"][k] is not None and r["knobs"][k] != val:
                C.fail("BP6", f"{r['vraag_id']}: {k}='{r['knobs'][k]}' but {r['pattern']} fixes {k}='{val}'", r["vraag_id"], k)
        v = next(x for o in bp["opgaven"] for x in o["vragen"] if x["vraag_id"] == r["vraag_id"])
        earlier = [x["number"] for x in by_opgave[r["opgave_id"]] if x["number"] < r["number"]]
        bad = [n for n in v["builds_on_vragen"] if n not in earlier]
        if bad:
            C.fail("BP6", f"{r['vraag_id']}: builds_on_vragen {bad} are not earlier vragen of {r['opgave_id']}", r["vraag_id"], "builds_on")
        if (r["knobs"].get("builds_on") == "ja") != bool(v["builds_on_vragen"]):
            C.fail("BP6", f"{r['vraag_id']}: builds_on={r['knobs'].get('builds_on')} but builds_on_vragen={v['builds_on_vragen']}",
                   r["vraag_id"], "builds_on")

    # BP7 shares
    shares = point_shares(recs, run.pidx, run.knobs)
    for d in tolerance_report(order, shares):
        what = "Bloom-mix" if d["what"] == "bloom" else d["what"]
        msg = (f"{what} '{d['value']}': {d['share']:.0%} planned ({d['points']:g} of {d['of']:g} p), ordered "
               f"{d['ordered']:.0%}")
        if d["slack"]:
            rep.info("BP7", msg + " — within the slack rule (one vraag/scorepunt would overshoot)")
        else:
            C.fail("BP7", msg + f" (tolerance ±{5 if d['what'] == 'bloom' else 10} pp)", None,
                   "scorepunten" if d["what"] == "bloom" else d["what"])

    # BP8 contexts
    avoid = [a.lower() for a in order.get("avoid_contexts") or [] if a]
    hist_pairs = []
    for h in run.history:
        tags = [t.lower() for t in h["context_tags"]]
        hist_pairs.append((h, {frozenset(p) for p in itertools.combinations(tags, 2)} if len(tags) >= 2 else {frozenset(tags)}))
    firsts = {}
    for o in bp["opgaven"]:
        if o.get("reused_from"):
            continue
        tags = [t.lower() for t in o["context_tags"]]
        mine = {frozenset(p) for p in itertools.combinations(tags, 2)} if len(tags) >= 2 else {frozenset(tags)}
        for h, pairs in hist_pairs:
            if mine & pairs:
                C.fail("BP8", f"{o['opgave_id']}: context tags {o['context_tags']} repeat {h['toets_id']} {h['opgave_id']} "
                              f"'{h['title']}' ({h['date']})", o["opgave_id"], "context")
        text = " ".join([o["title"], o["context"], *o["context_tags"]]).lower()
        for a in avoid:
            if a in text:
                C.fail("BP8", f"{o['opgave_id']}: context matches avoid_contexts '{a}'", o["opgave_id"], "context")
        if tags:
            if tags[0] in firsts:
                C.fail("BP8", f"{o['opgave_id']} and {firsts[tags[0]]} share the first tag '{tags[0]}' (vary the branche)",
                       o["opgave_id"], "context")
            firsts.setdefault(tags[0], o["opgave_id"])
        if not tags:
            rep.warn("BP8", f"{o['opgave_id']}: no context_tags (the planner fills them)")

    # BP9 figures, P15 last
    for o in bp["opgaven"]:
        for i, v in enumerate(sorted(o["vragen"], key=lambda x: x["number"])):
            codes = pattern_codes(v["pattern"])
            if any((run.pidx.get(c) or {}).get("needs_figure") for c in codes) and not (v.get("figure") or o.get("figures_planned")):
                C.fail("BP9", f"{v['vraag_id']}: pattern {v['pattern']} needs a figure but none is planned", v["vraag_id"], "pattern")
            if "P15" in codes and i != len(o["vragen"]) - 1:
                C.fail("BP9", f"{v['vraag_id']}: P15 is not the last vraag of {o['opgave_id']}", v["vraag_id"], "pattern")

    # BP10 coverage
    tested = defaultdict(set)
    for r in recs:
        for s in r["scorepunten"]:
            tested[(run.crit.get(s["criterion_id"]) or {}).get("group_id")].add(s["criterion_id"])
    coverage = []
    for g in matrix:
        allc = [c["criterion_id"] for c in run.groups[g]["criteria"]] if g in run.groups else []
        t = [c for c in allc if c in tested[g]]
        coverage.append({"group_id": g, "points": gp.get(g, 0), "criteria_tested": t,
                         "criteria_not_tested": [c for c in allc if c not in tested[g]]})
        rep.info("BP10", f"{g}: tested {', '.join(t) or '–'}; not tested {', '.join(coverage[-1]['criteria_not_tested']) or '–'}")
    given = {c["group_id"]: (sorted(c["criteria_tested"]), sorted(c["criteria_not_tested"])) for c in bp["coverage"]["per_group"]}
    if given and given != {c["group_id"]: (sorted(c["criteria_tested"]), sorted(c["criteria_not_tested"])) for c in coverage}:
        rep.warn("BP10", "the planner's coverage differs from the computed one (--write replaces it)")

    planned = {"bloom": as_shares(ordered_levels(shares["bloom"])),
               "knobs": {k: as_shares(v) for k, v in shares["knobs"].items() if v}}
    if "--write" in argv and not rep.failed:
        bp["planned_shares"] = planned
        bp["coverage"] = {"per_group": coverage}
        save_json(bp_path, bp)
        rep.info("BP7", f"planned_shares and coverage written to {bp_path.name}")
    rep.info("BP3", f"{len(bp['opgaven'])} opgaven, {len(vids)} vragen, {sum(r['points'] for r in recs)} points; "
                    f"Bloom {planned['bloom']}")
    rep.print_and_exit(str(R / "32_blueprint.check.json"))


if __name__ == "__main__":
    main(sys.argv)
