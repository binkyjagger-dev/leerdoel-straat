"""Shares by points and the tolerance rule of the toets-straat (specs/32 §1, §4; specs/34 BP7, V9).

Used by blueprint_check.py (planned shares), blueprint_report.py and realized.py (realised shares), so the plan and
the result are measured the same way. A record is one vraag:
  {vraag_id, opgave_id, number, first, points, pattern, knobs: {knob: value|None}, scorepunten: [{points, bloom, criterion_id}]}
Shares are conditional on applicability: route over calculation/schema vragen, schema over schema vragen,
builds_on over vragen that are not the first of their opgave. A combined pattern splits its points evenly
(specs/26 §4, bouwvraag 2). A knob value of None on an applicable vraag (e.g. a disputed label) is left out.
"""
from __future__ import annotations

from collections import defaultdict

from tcommon import BLOOM_ORDER, LABEL_KNOBS, kinds_of, knob_applies, pattern_codes

KNOB_TOL = 0.10
BLOOM_TOL = 0.05


def blueprint_records(bp: dict) -> list[dict]:
    recs = []
    for og in bp["opgaven"]:
        vs = sorted(og["vragen"], key=lambda v: v["number"])
        for i, v in enumerate(vs):
            recs.append({"vraag_id": v["vraag_id"], "opgave_id": og["opgave_id"], "number": v["number"], "first": i == 0,
                         "points": v["points"], "pattern": v["pattern"], "knobs": dict(v["knobs"]),
                         "scorepunten": [dict(s) for s in v["scorepunten"]], "reused": bool(og.get("reused_from"))})
    return recs


def point_shares(recs: list[dict], pidx: dict, knobs: dict) -> dict:
    """{'bloom': {level: pts}, 'knobs': {knob: {value: pts}}, 'units': {...}} — units are the movable sizes per
    knob value (vraag points; scorepunt points for Bloom), used by the slack rule."""
    bloom, units_b = defaultdict(float), defaultdict(list)
    kp = {k: defaultdict(float) for k in ["pattern"] + LABEL_KNOBS}
    units = {k: defaultdict(list) for k in kp}
    applicable = defaultdict(list)  # knob → [(vraag points, value)]
    for r in recs:
        for s in r["scorepunten"]:
            if s.get("bloom"):
                bloom[s["bloom"]] += s["points"]
                units_b[s["bloom"]].append(s["points"])
        codes = pattern_codes(r["pattern"])
        if codes and r["pattern"] != "NIEUW":
            for c in codes:
                kp["pattern"][c] += r["points"] / len(codes)
                units["pattern"][c].append(r["points"] / len(codes))
        kinds = kinds_of(r["pattern"], pidx)
        for k in LABEL_KNOBS:
            if k in ("route", "schema") and (not codes or r["pattern"] == "NIEUW"):
                continue
            if not knob_applies(knobs[k], kinds, r["first"]):
                continue
            v = (r["knobs"] or {}).get(k)
            if v is None:
                continue
            kp[k][v] += r["points"]
            units[k][v].append(r["points"])
    return {"bloom": dict(bloom), "knobs": {k: dict(v) for k, v in kp.items()},
            "units": {"bloom": {k: v for k, v in units_b.items()}, **{k: {x: y for x, y in v.items()} for k, v in units.items()}}}


def as_shares(pts: dict) -> dict:
    tot = sum(pts.values())
    return {k: round(v / tot, 3) for k, v in pts.items()} if tot else {}


def deviations(target: dict, pts: dict, units: dict, tol: float) -> list[dict]:
    """Per value: planned/realised points vs the ordered share. A deviation outside `tol` is still within tolerance
    when moving the smallest movable unit to the right side would overshoot beyond `tol` on the other side
    (specs/32 §4, slack rule). Returns one record per value outside tolerance (with `slack` True when only the slack
    rule keeps it in) — records with slack True are within tolerance."""
    out = []
    D = sum(pts.values())
    if not D:
        return out
    for v in sorted(set(target) | set(pts), key=str):
        want = target.get(v, 0.0) * D
        got = pts.get(v, 0.0)
        diff = got - want
        if abs(diff) <= tol * D + 1e-9:
            continue
        if diff > 0:
            cand = units.get(v, [])
        else:
            cand = [p for w, ps in units.items() if w != v for p in ps]
        if not cand:
            slack = True
        else:
            p = min(cand)
            new = diff - p if diff > 0 else diff + p
            slack = abs(new) > tol * D + 1e-9 and (new > 0) != (diff > 0)
        out.append({"value": v, "ordered": round(target.get(v, 0.0), 3), "share": round(got / D, 3),
                    "points": round(got, 3), "of": round(D, 3), "slack": slack})
    return out


def tolerance_report(order: dict, shares: dict) -> list[dict]:
    """All deviations of the Bloom mix (±5 pp) and the knob shares (±10 pp) against the order."""
    res = []
    bm = order.get("bloom_mix")
    if bm:
        for d in deviations(bm, shares["bloom"], shares["units"]["bloom"], BLOOM_TOL):
            res.append({"what": "bloom", **d})
    for k, target in (order.get("knobs") or {}).items():
        if not isinstance(target, dict) or k not in shares["knobs"]:
            continue
        for d in deviations(target, shares["knobs"][k], shares["units"][k], KNOB_TOL):
            res.append({"what": k, **d})
    return res


def group_points(recs: list[dict], crit: dict) -> dict:
    out = defaultdict(int)
    for r in recs:
        for s in r["scorepunten"]:
            out[(crit.get(s["criterion_id"]) or {}).get("group_id", "?")] += s["points"]
    return dict(out)


def ordered_levels(d: dict) -> dict:
    return dict(sorted(d.items(), key=lambda kv: BLOOM_ORDER.index(kv[0]) if kv[0] in BLOOM_ORDER else 99))
