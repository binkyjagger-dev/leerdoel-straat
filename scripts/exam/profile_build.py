#!/usr/bin/env python3
"""E7 — rebuild the subject's reference profile from the bank's labels (specs/26 §4, §6).

Usage: profile_build.py <subject> [--bank <dir>] [--subjects <dir>] [--base <file>] [--knobs <file>]

Reads the bank (register.json, labels/<exam_id>.json, links/<exam_id>.json) and writes profiel/:
  referentieprofiel.json  per knob: per value points + share, pooled and per exam (schema reference_profile)
  referentieprofiel.md    the same as Dutch tables, with the exams it is based on and the points left out
  patronen_stats.json     per pattern: questions, points (sum, min, max), Bloom and SOLO spread, example candidates
Shares are by points and conditional on applicability: route over calculation/schema patterns, schema over schema
patterns, builds_on over questions that are not the first of their opgave. Disputed fields, not-applicable knobs,
unlinked scorepunten (bloom, combination) and NIEUW patterns are left out of their knob's totals and reported as
`excluded`; a NIEUW question is also left out of route and schema until its pattern is decided. A '+'-combination of two patterns splits the question's points evenly over both codes.
`combination` and `bloom` are recomputed from the links (labels survive a bank --rebuild).
Without labels for the subject, subjects/<s>/toets/seed_profile.json is used (source "seed-…"); without a seed the
profile says that no reference exists (source "none"). Conservation: per exam and knob the counted plus excluded
points must equal the exam's labelled points, else the script fails and writes nothing.
The profile is never edited by hand.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

from lcommon import computed_fields
from ecommon import BLOOM_ORDER, ROOT, Report, load_json, save_json, validate_def, validate_schema
from tcommon import (BASE_PATTERNS_PATH, KNOBS_PATH, LABEL_KNOBS, exam_label, kinds_of, knob_applies, knob_index,
                     merged_catalogue, pattern_codes, shares_from_points)

PROFILE_KNOBS = ["pattern", "bloom"] + LABEL_KNOBS + ["combination"]
KNOB_LABEL_NL = {"bloom": "Bloom (per scorepunt)"}
REASON_NL = {"disputed": "geschil", "not_applicable": "niet van toepassing", "unlinked": "geen koppeling",
             "nieuw": "nieuw patroon"}
MONTHS = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
EPS = 1e-6


def opt(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv else None


def value_order(knob: str, knobs: dict, cat: dict) -> list[str]:
    if knob == "bloom":
        return BLOOM_ORDER
    if knob == "pattern":
        return [p["code"] for p in cat["patterns"]]
    vals = knobs[knob]["values"]
    return vals if isinstance(vals, list) else []


def sort_values(d: dict, order: list[str]) -> dict:
    return dict(sorted(d.items(), key=lambda kv: (order.index(kv[0]) if kv[0] in order else len(order), kv[0])))


def question_values(l: dict, knobs: dict, pidx: dict) -> dict[str, list[tuple[str, float]]]:
    """knob → [(value or '!reason', points)] for one labelled question."""
    P, conf = l["points"], l["confidence"]
    out: dict[str, list[tuple[str, float]]] = {}
    pat = l.get("pattern")
    if pat is None or conf.get("pattern") == "disputed":
        out["pattern"] = [("!disputed", P)]
    elif pat == "NIEUW":
        out["pattern"] = [("!nieuw", P)]
    else:
        codes = pattern_codes(pat)
        out["pattern"] = [(c, P / len(codes)) for c in codes]
    for k in LABEL_KNOBS:
        v = l.get(k)
        if k in ("route", "schema") and pat == "NIEUW":
            out[k] = [("!nieuw", P)]  # applicability depends on the undecided pattern (specs/26 §4, bouwvraag 6)
        elif k == "builds_on" and l.get("first_of_opgave"):
            out[k] = [("!not_applicable", P)]
        elif v is not None:
            out[k] = [(v, P)]
        elif conf.get(k) == "disputed":
            out[k] = [("!disputed", P)]
        else:
            out[k] = [("!not_applicable", P)]
    n = l.get("combination") or 0
    out["combination"] = [(str(n), P)] if n else [("!unlinked", P)]
    sb = l.get("scorepunt_bloom") or []
    out["bloom"] = [(s["bloom"] or "!unlinked", s["points"]) for s in sb] or [("!unlinked", P)]
    return out


def from_labels(subject: str, bank: Path, reg: dict, files: dict, knobs: dict, cat: dict, rep: Report):
    pidx = {p["code"]: p for p in cat["patterns"]}
    exams, pooled, pooled_excl = [], defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float))
    stats = defaultdict(lambda: {"n_questions": 0, "points": {"sum": 0.0, "min": None, "max": None},
                                 "bloom": defaultdict(float), "solo": defaultdict(float), "examples": []})
    n_questions = 0
    for e in reg["exams"]:
        eid = e["exam_id"]
        if eid not in files:
            continue
        lab = load_json(files[eid])
        errs = validate_def(lab, "item_labels.schema.json", "bank_file")
        if errs:
            rep.fail("PB1", f"labels/{eid}.json: {errs[0]}")
            continue
        links = defaultdict(list)
        lp = bank / "links" / f"{eid}.json"
        for sp in (load_json(lp)["scorepunten"] if lp.exists() else []):
            links[sp["question_id"]].append(sp)
        kp, ke = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float))
        total = 0
        for l in lab["questions"]:
            l = {**l, **computed_fields(links.get(l["question_id"], []))} if lp.exists() else l
            total += l["points"]
            vals = question_values(l, knobs, pidx)
            for k, pairs in vals.items():
                for v, p in pairs:
                    if v.startswith("!"):
                        ke[k][v[1:]] += p
                    else:
                        kp[k][v] += p
            # pattern statistics
            if vals["pattern"][0][0].startswith("!"):
                continue
            share = 1 / len(vals["pattern"])
            for code, p in vals["pattern"]:
                st = stats[code]
                st["n_questions"] += 1
                st["points"]["sum"] += p
                st["points"]["min"] = l["points"] if st["points"]["min"] is None else min(st["points"]["min"], l["points"])
                st["points"]["max"] = l["points"] if st["points"]["max"] is None else max(st["points"]["max"], l["points"])
                for v, bp in vals["bloom"]:
                    if not v.startswith("!"):
                        st["bloom"][v] += bp * share
                if l.get("solo"):
                    st["solo"][l["solo"]] += p
                if l.get("example_quality") and l["confidence"].get("example_quality") != "disputed":
                    st["examples"].append({"exam_id": eid, "question_number": l["question_number"],
                                           "example_quality": l["example_quality"],
                                           "reason": l.get("example_quality_reason"), "points": l["points"]})
        n_questions += len(lab["questions"])
        for k in PROFILE_KNOBS:
            got = sum(kp[k].values()) + sum(ke[k].values())
            if abs(got - total) > EPS:
                rep.fail("PB2", f"{eid} {k}: counted + excluded = {got:g} points, labelled points {total} (conservation)")
            for v, p in kp[k].items():
                pooled[k][v] += p
            for r, p in ke[k].items():
                pooled_excl[k][r] += p
        if total != e["max_score"]:
            rep.warn("PB2", f"{eid}: labelled points {total} != max_score {e['max_score']}")
        exams.append({"exam_id": eid, "points": total, "n_questions": len(lab["questions"]),
                      "knobs": {k: {v: round(p, 3) for v, p in sort_values(kp[k], value_order(k, knobs, cat)).items()}
                                for k in PROFILE_KNOBS},
                      "excluded": {k: {r: round(p, 3) for r, p in sorted(ke[k].items())} for k in PROFILE_KNOBS if ke[k]}})
    labels_nl = ", ".join(exam_label(x["exam_id"]) for x in exams)
    profile = {"subject": subject, "source": "bank-labels",
               "label": f"referentie: {len(exams)} examen{'s' if len(exams) != 1 else ''} ({labels_nl})",
               "note": None, "n_exams": len(exams), "n_questions": n_questions,
               "points": sum(x["points"] for x in exams), "by": "points",
               "pooled": {k: shares_from_points(sort_values(pooled[k], value_order(k, knobs, cat))) for k in PROFILE_KNOBS},
               "excluded": {k: {r: round(p, 3) for r, p in sorted(pooled_excl[k].items())} for k in PROFILE_KNOBS if pooled_excl[k]},
               "unknown_knobs": [], "exams": exams}
    qrank = {"goed": 0, "bruikbaar": 1, "ongeschikt": 2}
    pstats = {}
    for code in [p["code"] for p in cat["patterns"]] + sorted(set(stats) - {p["code"] for p in cat["patterns"]}):
        if code not in stats:
            continue
        st = stats[code]
        pstats[code] = {"n_questions": st["n_questions"],
                        "points": {"sum": round(st["points"]["sum"], 3), "min": st["points"]["min"], "max": st["points"]["max"]},
                        "bloom": {k: round(v, 3) for k, v in sort_values(st["bloom"], BLOOM_ORDER).items()},
                        "solo": {k: round(v, 3) for k, v in sort_values(st["solo"], value_order("solo", knobs, cat)).items()},
                        "examples": sorted(st["examples"], key=lambda x: (qrank.get(x["example_quality"], 3), x["exam_id"],
                                                                          x["question_number"]))}
    return profile, {"subject": subject, "source": "bank-labels", "patterns": pstats}


def seed_label(source: str) -> str:
    m = re.search(r"(\d{4})-(\d{2})", source)
    return f"referentie: voorlopig, analyse {MONTHS[int(m.group(2)) - 1]} {m.group(1)}" if m else "referentie: voorlopig"


def from_seed(seed: dict, knobs: dict, cat: dict, rep: Report):
    for e in seed["exams"]:
        for k, vals in e["knobs"].items():
            got = sum(vals.values()) + sum((e.get("excluded") or {}).get(k, {}).values())
            if abs(got - e["points"]) > EPS:
                rep.fail("PB2", f"seed {e['exam_id']} {k}: {got:g} points, exam points {e['points']} (conservation)")
    profile = {**seed, "label": seed.get("label") or seed_label(seed["source"]),
               "n_questions": seed.get("n_questions") or sum(len(e.get("questions", [])) for e in seed["exams"])}
    stats = defaultdict(lambda: {"n_questions": 0, "points": {"sum": 0, "min": None, "max": None},
                                 "bloom": defaultdict(float), "solo": defaultdict(float), "examples": []})
    for e in seed["exams"]:
        for q in e.get("questions", []):
            codes = pattern_codes(q.get("pattern"))
            for c in codes:
                st = stats[c]
                p = q["points"] / len(codes)
                st["n_questions"] += 1
                st["points"]["sum"] += p
                st["points"]["min"] = q["points"] if st["points"]["min"] is None else min(st["points"]["min"], q["points"])
                st["points"]["max"] = q["points"] if st["points"]["max"] is None else max(st["points"]["max"], q["points"])
                if q.get("bloom"):
                    st["bloom"][q["bloom"]] += p
                if q.get("solo"):
                    st["solo"][q["solo"]] += p
    pstats = {c: {"n_questions": s["n_questions"],
                  "points": {"sum": round(s["points"]["sum"], 3), "min": s["points"]["min"], "max": s["points"]["max"]},
                  "bloom": {k: round(v, 3) for k, v in sort_values(s["bloom"], BLOOM_ORDER).items()},
                  "solo": {k: round(v, 3) for k, v in sort_values(s["solo"], value_order("solo", knobs, cat)).items()},
                  "examples": []}
              for c, s in sorted(stats.items())}
    return profile, {"subject": seed["subject"], "source": seed["source"], "patterns": pstats}


def empty(subject: str, knobs: dict):
    unknown = ["pattern", "bloom"] + [k for k in LABEL_KNOBS] + ["combination"]
    return ({"subject": subject, "source": "none", "label": "referentie: geen (nog geen gelabelde examens)",
             "note": "De examenbank heeft nog geen labels en het vak heeft geen seed-profiel.", "n_exams": 0,
             "n_questions": 0, "points": 0, "by": "points", "pooled": {}, "unknown_knobs": unknown, "exams": []},
            {"subject": subject, "source": "none", "patterns": {}})


def pct(x: float) -> str:
    return f"{x * 100:.0f} %".replace(".", ",")


def num(x: float) -> str:
    return (f"{x:.1f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))).replace(".", ",")


def render_md(profile: dict, stats: dict, knobs: dict, cat: dict) -> str:
    names = {p["code"]: p["name"] for p in cat["patterns"]}
    exams = profile["exams"]
    L = [f"# Referentieprofiel — {profile['subject']}", "",
         f"**{profile['label'][0].upper() + profile['label'][1:]}** · {profile['n_exams']} examen(s), "
         f"{profile.get('n_questions') or 0} vragen, {num(profile['points'])} punten. "
         "Aandelen zijn per punt en gelden alleen over de vragen waarop de knop van toepassing is.", ""]
    if profile.get("note"):
        L += [f"*{profile['note']}*", ""]
    L += ["*Dit bestand wordt gebouwd door `scripts/exam/profile_build.py` uit `examenbank/labels/`; niet met de hand bewerken.*", ""]
    for k in PROFILE_KNOBS:
        title = KNOB_LABEL_NL.get(k) or (knobs[k]["label"] if k in knobs else k)
        if k == "bloom" and profile["source"] != "bank-labels":
            title = "Bloom (per vraag)"
        L += [f"## {title}", ""]
        if k in profile["unknown_knobs"] or k not in profile["pooled"]:
            L += ["Onbekend (nog niet gelabeld).", ""]
            continue
        pooled = profile["pooled"][k]
        head = "| waarde | eindexamen (alle) | " + " | ".join(exam_label(e["exam_id"]) for e in exams) + " |"
        L += [head, "|" + "---|" * (2 + len(exams))]
        for v, d in pooled.items():
            cells = []
            for e in exams:
                ek = e["knobs"].get(k, {})
                tot = sum(ek.values())
                cells.append(f"{num(ek.get(v, 0))} p · {pct(ek.get(v, 0) / tot) if tot else '–'}")
            label = f"{v} {names[v]}" if k == "pattern" and v in names else v
            L.append(f"| {label} | {num(d['points'])} p · {pct(d['share'])} | " + " | ".join(cells) + " |")
        excl = (profile.get("excluded") or {}).get(k)
        if excl:
            L += ["", "Weggelaten: " + ", ".join(f"{num(p)} p {REASON_NL.get(r, r)}" for r, p in excl.items()) + "."]
        L.append("")
    if stats["patterns"]:
        L += ["## Patronen: voorbeelden", "", "| patroon | vragen | punten (min–max) | voorbeelden (goed eerst) |", "|---|---|---|---|"]
        for code, s in stats["patterns"].items():
            ex = ", ".join(f"{exam_label(x['exam_id'])} v{x['question_number']} ({x['example_quality']})" for x in s["examples"][:4]) or "–"
            L.append(f"| {code} {names.get(code, '')} | {s['n_questions']} | {num(s['points']['sum'])} "
                     f"({s['points']['min']}–{s['points']['max']}) | {ex} |")
        L.append("")
    return "\n".join(L)


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[1].startswith("--"):
        print(__doc__)
        sys.exit(2)
    subject = argv[1]
    rep = Report("profile_build")
    subjects = Path(opt(argv, "--subjects")) if opt(argv, "--subjects") else ROOT / "subjects"
    bank = Path(opt(argv, "--bank")) if opt(argv, "--bank") else subjects / subject / "examenbank"
    knobs = knob_index(load_json(opt(argv, "--knobs") or KNOBS_PATH))
    cat = merged_catalogue(subject, Path(opt(argv, "--base") or BASE_PATTERNS_PATH), subjects)
    reg = load_json(bank / "register.json") if (bank / "register.json").exists() else {"exams": []}
    files = {e["exam_id"]: bank / "labels" / f"{e['exam_id']}.json" for e in reg["exams"]
             if (bank / "labels" / f"{e['exam_id']}.json").exists()}
    seed_path = subjects / subject / "toets" / "seed_profile.json"
    if files:
        profile, stats = from_labels(subject, bank, reg, files, knobs, cat, rep)
    elif seed_path.exists():
        seed = load_json(seed_path)
        for e in validate_schema(seed, "reference_profile.schema.json")[:5]:
            rep.fail("PB1", f"seed_profile.json: {e}")
        if rep.failed:
            rep.print_and_exit()
        profile, stats = from_seed(seed, knobs, cat, rep)
        rep.info("PB1", f"no labels in {bank}/labels: using the seed profile ({seed['source']})")
    else:
        profile, stats = empty(subject, knobs)
        rep.warn("PB1", f"no labels and no seed profile for {subject}: the reference is empty")
    for e in validate_schema(profile, "reference_profile.schema.json")[:5]:
        rep.fail("PB1", f"referentieprofiel.json: {e}")
    for e in validate_def(stats, "reference_profile.schema.json", "pattern_stats")[:5]:
        rep.fail("PB1", f"patronen_stats.json: {e}")
    if rep.failed:
        rep.print_and_exit()  # nothing written
    out = bank / "profiel"
    save_json(out / "referentieprofiel.json", profile)
    save_json(out / "patronen_stats.json", stats)
    (out / "referentieprofiel.md").write_text(render_md(profile, stats, knobs, cat), encoding="utf-8")
    rep.info("PB2", f"{profile['label']}: {profile['n_exams']} exams, {num(profile['points'])} points -> {out}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
