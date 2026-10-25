#!/usr/bin/env python3
"""M4 — merge judgements A/B, check quotes, compute confidence, assign gradations (specs/12 §2–4).

Usage: gradation.py <run_dir> [--judges A,B] [--repair 13_judgements.R]

Reads 11_method_units.json (+text/), 10_criteria.json, 13_judgements.<J>/<unit>.json per judge.
A repair judgement file set (judge "R") decides the pairs it contains: it replaces the judge(s) that disagree with it.
Writes 13_judgements.json (merged), 14_mappings.json, 14_findings.json.
"""
from __future__ import annotations

import glob
import sys
from collections import defaultdict
from pathlib import Path

from mcommon import MAX_QUOTE_WORDS, Report, load_json, quote_in_text, read_text, save_json, validate_schema, words

STRENGTH = {"explains": 3, "practises": 2, "mentions": 1, "none": 0}


def load_judge(run_dir: Path, j: str) -> dict:
    out = {}
    for f in sorted(glob.glob(str(run_dir / f"13_judgements.{j}" / "*.json"))):
        d = load_json(f)
        errs = validate_schema(d, "judgements.schema.json")
        if errs:
            sys.exit(f"invalid judgement file {f}: {errs[0]}")
        for jd in d["judgements"]:
            out[(jd["criterion_id"], d["unit_id"])] = jd
    return out


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    judges = (argv[argv.index("--judges") + 1] if "--judges" in argv else "A,B").split(",")
    rep = Report("gradation")
    method = load_json(run_dir / "11_method_units.json")
    tolerant = method["method"]["text_extraction"] in ("ocr", "mixed")
    units = {u["unit_id"]: u for u in method["units"]}
    crit = {}
    for g in load_json(run_dir / "10_criteria.json")["groups"]:
        for c in g["criteria"]:
            crit[c["criterion_id"]] = {"group_id": g["group_id"]}

    J = {j: load_judge(run_dir, j) for j in judges}
    R = load_judge(run_dir, "R") if (run_dir / "13_judgements.R").exists() else {}
    pairs = set().union(*(set(d) for d in J.values())) | set(R)  # R may add a missing link
    texts = {}

    def text_of(uid):
        if uid not in texts:
            texts[uid] = read_text(run_dir, units[uid].get("text_ref"))
        return texts[uid]

    def valid(jd, uid):
        q = jd.get("quote")
        if not q or jd["treatment"] == "none":
            return False, 0.0
        if words(q) > MAX_QUOTE_WORDS:
            return False, 0.0
        return quote_in_text(q, text_of(uid), tolerant)

    merged, voided = [], []
    for (cid, uid) in sorted(pairs):
        if cid not in crit or uid not in units:
            rep.warn("MS1", f"judgement on unknown pair {cid} x {uid}")
            continue
        js = {j: J[j].get((cid, uid), {"treatment": "none", "quote": None}) for j in judges}
        overruled = False
        if (cid, uid) in R:
            # repair decides the pair: it replaces every judge that disagrees with it
            r = R[(cid, uid)]
            against = [j for j in js if js[j]["treatment"] != r["treatment"]]
            for j in against:
                js[j] = dict(r, _repaired=True)
            overruled = len(against) == len(js)
        tr = {j: js[j]["treatment"] for j in js}
        vq = {j: valid(js[j], uid) for j in js}
        strengths = sorted(((STRENGTH[tr[j]], j) for j in js), reverse=True)
        top_j = strengths[0][1]
        treatment = tr[top_j]
        if all(t == "none" for t in tr.values()):
            continue
        # confidence (specs/12 §4)
        tset = set(tr.values())
        if len(tset) == 1:
            conf = "high" if all(v[0] for v in vq.values()) and not overruled else "medium"
        elif "none" in tset:
            conf = "low"
        elif tset == {"explains", "practises"}:
            conf = "medium"
            # stronger quote decides; default practises
            valids = [j for j in js if vq[j][0]]
            treatment = tr[valids[0]] if len(valids) == 1 else "practises"
            top_j = next(j for j in js if tr[j] == treatment)
        else:
            conf = "low"  # mentions vs stronger
        # choose quote: from the judge whose treatment is the final one and quote valid
        quote_j = next((j for j in js if tr[j] == treatment and vq[j][0]), None)
        if quote_j is None:
            voided.append({"criterion_id": cid, "unit_id": uid, "treatment": treatment,
                           "judges": {j: {"treatment": tr[j], "quote": js[j].get("quote"), "quote_valid": vq[j][0]} for j in js},
                           "reason": "invalid_quote"})
            continue
        jd = js[quote_j]
        merged.append({
            "criterion_id": cid, "group_id": crit[cid]["group_id"], "unit_id": uid,
            "treatment": treatment, "quote": jd["quote"], "quote_page": jd.get("quote_page"),
            "confidence": conf,
            "judges": {j: {"treatment": tr[j], "quote_valid": vq[j][0], "aspect": js[j].get("aspect"), "repaired": js[j].get("_repaired", False)} for j in js},
            "aspect": jd.get("aspect"), "second_quote": jd.get("second_quote"),
        })
    save_json(run_dir / "13_judgements.json", {"merged": merged, "voided": voided})

    # gradation per criterion in order (specs/12 §2)
    order = {u["unit_id"]: u.get("order") or 0 for u in method["units"]}
    by_crit = defaultdict(list)
    for m in merged:
        by_crit[m["criterion_id"]].append(m)
    links, findings = [], []
    scope = set(load_json(run_dir / "12_candidates.json")["scope_paragraphs"]) if (run_dir / "12_candidates.json").exists() else set(units)
    cand = load_json(run_dir / "12_candidates.json") if (run_dir / "12_candidates.json").exists() else None
    in_scope = (cand.get("scope_criteria") or [c["criterion_id"] for c in cand["per_criterion"]]) if cand else list(crit)
    in_scope_set = set(in_scope)
    for cid, ms in by_crit.items():
        ms.sort(key=lambda m: order[m["unit_id"]])
        first_explain = next((m for m in ms if m["treatment"] == "explains"), None)
        for m in ms:
            note = None
            if m["treatment"] == "explains":
                if m is first_explain:
                    grad = "leert"
                else:
                    grad = "herhaalt"
                    if m.get("aspect") and first_explain.get("aspect") and m["aspect"] != first_explain["aspect"]:
                        note = f"breidt uit: {m['aspect']}"
            elif m["treatment"] == "practises":
                grad = "oefent"
                if first_explain and order[m["unit_id"]] < order[first_explain["unit_id"]]:
                    note = "oefent vóór uitleg"
                    findings.append({"criterion_id": cid, "unit_id": m["unit_id"], "finding": "oefent vóór uitleg"})
            else:
                grad = "noemt"
            if m.get("second_quote"):
                note = (note + "; " if note else "") + f"tweede citaat: {m['second_quote']}"
            links.append({k: m[k] for k in ("criterion_id", "group_id", "unit_id", "treatment", "quote", "quote_page", "confidence", "judges")}
                         | {"gradation": grad, "verifier": None, "note": note, "status": "proposed"})
        if first_explain is None and cid in in_scope_set:
            findings.append({"criterion_id": cid, "unit_id": None, "finding": "alleen geoefend" if any(m["treatment"] == "practises" for m in ms) else "alleen genoemd"})
    # criteria in scope without any link
    for cid in in_scope:
        if cid not in by_crit:
            findings.append({"criterion_id": cid, "unit_id": None, "finding": "niet in deze methode"})
    # paragraphs without link
    linked_paras = {l["unit_id"] for l in links if l["gradation"] != "noemt"}
    for uid in sorted(scope):
        if uid not in linked_paras:
            findings.append({"criterion_id": None, "unit_id": uid, "finding": "buiten syllabus (geen koppeling)"})
    # same quote across groups (J-M5)
    seen = defaultdict(set)
    for l in links:
        seen[l["quote"].strip().lower()].add(l["group_id"])
    for q, gs in seen.items():
        if len(gs) > 1:
            findings.append({"criterion_id": None, "unit_id": None, "finding": f"zelfde citaat bij groepen {sorted(gs)}: '{q[:60]}…'"})

    out = {"links": links, "voided": voided, "findings": findings}
    errs = validate_schema(out, "mappings.schema.json")
    for e in errs:
        rep.fail("MS1", e)
    save_json(run_dir / "14_mappings.json", out)
    save_json(run_dir / "14_findings.json", {"findings": findings})
    from collections import Counter
    rep.info("M4", f"{len(links)} links: {dict(Counter(l['gradation'] for l in links))}; confidence {dict(Counter(l['confidence'] for l in links))}; voided {len(voided)}; findings {len(findings)}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
