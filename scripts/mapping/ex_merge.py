#!/usr/bin/env python3
"""M8b — merge exercise judgements A/B (+R), check quotes, confidence, Bloom reconciliation (specs/12 §6.2–6.3).

Usage: ex_merge.py <run_dir>

Reads 11_method_units.json (+text/), 10_criteria.json, 14_mappings.json, 12_candidates.json, 17_ex_candidates.json,
18_ex_judgements.<A|B|R>/<paragraph>.json and the subject's effective verb table.
Writes 18_ex_mappings.json (links, voided, findings).
"""
from __future__ import annotations

import glob
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import bloom_rank, load_bloom_rules, stem_verb  # noqa: E402
from mcommon import MAX_QUOTE_WORDS, Report, load_json, quote_in_text, read_text, save_json, validate_schema, words  # noqa: E402

CONF = ["low", "medium", "high"]
CALC = re.compile(r"(=|€|%)\s*-?\d|\d\s*(=|%|€)")


def load_judge(run_dir: Path, j: str) -> dict:
    """(sub-question, criterion) -> link; sub-questions judged -> set."""
    links, judged = {}, set()
    for f in sorted(glob.glob(str(run_dir / f"18_ex_judgements.{j}" / "*.json"))):
        d = load_json(f)
        errs = validate_schema(d, "ex_judgements.schema.json")
        if errs:
            sys.exit(f"invalid exercise judgement file {f}: {errs[0]}")
        for it in d["items"]:
            judged.add(it["unit_id"])
            for l in it["links"]:
                links[(it["unit_id"], l["criterion_id"])] = l
    return {"links": links, "judged": judged}


def computed(answer: str, question: str) -> bool:
    """The answer contains a calculation result the student had to produce: a number next to =, € or %
    that does not already occur in the question (a given number read back is not a calculation)."""
    given = set(re.findall(r"\d+(?:[.,]\d+)?", question))
    for m in CALC.finditer(answer):
        nums = re.findall(r"\d+(?:[.,]\d+)?", answer[max(0, m.start() - 12):m.end() + 12])
        if any(n not in given for n in nums):
            return True
    return False


def verb_levels(rules: dict, verb: str | None) -> list[str]:
    if not verb:
        return []
    v = stem_verb(verb.lower())
    lv = [l for l, vs in rules["verbs"].items() if any(stem_verb(x) == v for x in vs)]
    for k, ls in rules.get("ambiguous", {}).items():
        if stem_verb(k) == v:
            lv += [l for l in ls if l not in lv]
    return lv


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("ex_merge")
    run = load_json(run_dir / "run.json")
    rules = load_bloom_rules(run["subject"])
    method = load_json(run_dir / "11_method_units.json")
    tolerant = method["method"]["text_extraction"] in ("ocr", "mixed")
    units = {u["unit_id"]: u for u in method["units"]}
    order = {u["unit_id"]: u.get("order") or 0 for u in method["units"]}
    crit = {}
    for g in load_json(run_dir / "10_criteria.json")["groups"]:
        for c in g["criteria"]:
            crit[c["criterion_id"]] = {"group_id": g["group_id"], "bloom": c["bloom"]}
    cand = load_json(run_dir / "17_ex_candidates.json")
    para_of = {x["unit_id"]: x["paragraph_id"] for x in cand["per_subquestion"]}
    cand_a = load_json(run_dir / "12_candidates.json")
    scope_crit = cand_a.get("scope_criteria") or [c["criterion_id"] for c in cand_a["per_criterion"]]
    leert = {l["criterion_id"]: l["unit_id"] for l in load_json(run_dir / "14_mappings.json")["links"] if l["gradation"] == "leert"}

    J = {j: load_judge(run_dir, j) for j in ("A", "B")}
    R = load_judge(run_dir, "R") if (run_dir / "18_ex_judgements.R").exists() else {"links": {}, "judged": set()}
    for j in J:
        missing = set(para_of) - J[j]["judged"]
        if missing:
            rep.fail("MS1", f"judge {j} has no item for {len(missing)} sub-questions, e.g. {sorted(missing)[:3]}")

    def valid(l, uid):
        q = l.get("quote") if l else None
        if not q or words(q) > MAX_QUOTE_WORDS:
            return False
        return quote_in_text(q, read_text(run_dir, units[uid].get("text_ref")), tolerant)[0]

    pairs = set(J["A"]["links"]) | set(J["B"]["links"]) | set(R["links"])
    links, voided = [], []
    for (uid, cid) in sorted(pairs):
        if uid not in para_of or cid not in crit:
            rep.warn("MS1", f"judgement on unknown pair {uid} x {cid}")
            continue
        js = {j: J[j]["links"].get((uid, cid)) for j in ("A", "B")}
        repaired = None
        if (uid, cid) in R["links"]:
            r = R["links"][(uid, cid)]
            # R decides the pairs it re-judges: a rejection removes the link,
            # a link replaces the judge that lacked it (else B)
            if r.get("treatment") == "none":
                continue
            target = next((j for j in ("A", "B") if not js[j]), "B")
            js[target] = r
            repaired = target
        present = [j for j in js if js[j]]
        if not present:
            continue
        vq = {j: valid(js[j], uid) for j in present}
        if not any(vq.values()):
            voided.append({"criterion_id": cid, "unit_id": uid, "reason": "invalid_quote",
                           "judges": {j: {"quote": js[j].get("quote")} for j in present}})
            continue
        notes = []
        if len(present) == 2:
            blooms = {js[j]["bloom"] for j in present}
            conf = "high" if len(blooms) == 1 and all(vq.values()) else "medium"
            if len(blooms) == 1:
                bloom = blooms.pop()
            else:
                by_table = [js[j]["bloom"] for j in present if js[j]["bloom"] in verb_levels(rules, js[j].get("bloom_verb"))]
                bloom = by_table[0] if len(set(by_table)) == 1 else min((js[j]["bloom"] for j in present), key=bloom_rank)
                notes.append(f"bloom A: {js['A']['bloom']} / B: {js['B']['bloom']}")
        else:
            conf = "low"
            bloom = js[present[0]]["bloom"]
        src = next(j for j in present if vq[j])
        jd = js[src]
        verb = jd.get("bloom_verb")
        if repaired:
            bloom = js[repaired]["bloom"]  # R's level stands
        # MB1: where the verb gives no level, the answer form corrects it; then the verb table checks the result
        lv = verb_levels(rules, verb)
        answer = read_text(run_dir, units[uid].get("answer_ref"))
        if not lv and not repaired and answer and computed(answer, read_text(run_dir, units[uid].get("text_ref")))                 and bloom_rank(bloom) < bloom_rank("toepassen"):
            notes.append(f"antwoord is een berekening: {bloom} → toepassen")
            bloom = "toepassen"
        if lv and bloom not in lv:
            notes.append(f"werkwoord '{verb}' = {'/'.join(lv)} volgens tabel")
            conf = min(conf, "medium", key=CONF.index)
        links.append({
            "criterion_id": cid, "group_id": crit[cid]["group_id"], "unit_id": uid, "paragraph_id": para_of[uid],
            "bloom": bloom, "bloom_verb": verb, "quote": jd["quote"], "answer_checked": bool(jd.get("answer_checked")),
            "confidence": conf, "confidence_judged": conf,
            "judges": {j: ({"bloom": js[j]["bloom"], "quote_valid": vq[j], "repaired": repaired == j} if js[j] else None) for j in ("A", "B")},
            "verifier": None, "note": "; ".join(notes) or None, "status": "proposed"})

    # tevens: two criteria on one sub-question
    per_uid = defaultdict(list)
    for l in links:
        per_uid[l["unit_id"]].append(l)
    for uid, ls in per_uid.items():
        if len(ls) > 1:
            for l in ls:
                l["note"] = "; ".join(x for x in (l["note"], "tevens: " + ", ".join(o["criterion_id"] for o in ls if o is not l)) if x)

    findings = []
    for uid in sorted(para_of):
        if uid not in per_uid:
            findings.append({"criterion_id": None, "unit_id": uid, "finding": "oefenstof buiten syllabus"})
    seen, scope_set = set(), set(scope_crit)
    for l in links:
        cid, pid = l["criterion_id"], l["paragraph_id"]
        if cid in leert and order[leert[cid]] > order[pid] and (cid, pid) not in seen:
            findings.append({"criterion_id": cid, "unit_id": l["unit_id"], "finding": f"oefent vóór uitleg (leert in {leert[cid]})"})
            seen.add((cid, pid))
        elif cid not in leert and cid in scope_set and (cid, None) not in seen:
            findings.append({"criterion_id": cid, "unit_id": l["unit_id"], "finding": "geoefend zonder uitleg"})
            seen.add((cid, None))
    by_crit = defaultdict(list)
    for l in links:
        by_crit[l["criterion_id"]].append(l)
    for cid in scope_crit:
        ls = by_crit.get(cid)
        if not ls:
            findings.append({"criterion_id": cid, "unit_id": None, "finding": "niet geoefend"})
            continue
        top = max(ls, key=lambda l: bloom_rank(l["bloom"]))
        if bloom_rank(top["bloom"]) < bloom_rank(crit[cid]["bloom"]):
            findings.append({"criterion_id": cid, "unit_id": top["unit_id"],
                             "finding": f"bloom niet bereikt: hoogste {top['bloom']}, criterium {crit[cid]['bloom']}"})

    out = {"links": links, "voided": voided, "findings": findings}
    for e in validate_schema(out, "ex_mappings.schema.json")[:5]:
        rep.fail("MS1", e)
    save_json(run_dir / "18_ex_mappings.json", out)
    from collections import Counter
    rep.info("M8b", f"{len(links)} exercise links on {len(per_uid)}/{len(para_of)} sub-questions; "
             f"confidence {dict(Counter(l['confidence'] for l in links))}; bloom {dict(Counter(l['bloom'] for l in links))}; "
             f"voided {len(voided)}; findings {dict(Counter(f['finding'].split(':')[0].split(' (')[0] for f in findings))}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
