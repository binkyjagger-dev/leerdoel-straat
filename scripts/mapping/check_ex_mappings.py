#!/usr/bin/env python3
"""Deterministic checks on 18_ex_mappings.json (specs/14 §1 MQ2, MB1, MC1; §6) and verdict application.

Usage: check_ex_mappings.py <run_dir> [--verification 19_ex_verification.json]

With --verification the verifier's verdicts are written into 18_ex_mappings.json. Idempotent: confidence is
recomputed from `confidence_judged` each time; a dispute the repair judge already settled the verifier's way
is recorded as `resolved`.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import BLOOM_ORDER, load_bloom_rules  # noqa: E402
from ex_merge import verb_levels  # noqa: E402
from mcommon import MAX_QUOTE_WORDS, Report, load_json, norm, quote_in_text, read_text, save_json, validate_schema, words  # noqa: E402

CONF = ["low", "medium", "high"]
SEPARABLE = ("samen", "terug", "door", "mee", "voor", "toe", "aan", "uit", "af", "op", "in", "na", "om")


def verb_in_text(verb: str, text: str) -> bool:
    """Infinitive found in the question: 'berekenen' ~ 'bereken', 'toelichten' ~ 'licht … toe'."""
    t = norm(text)
    v = norm(verb).split()[0] if norm(verb) else ""
    root = v[:-2] if v.endswith("en") else v
    if root and root in t:
        return True
    words_ = t.split()
    for p in SEPARABLE:
        if v.startswith(p) and len(root) > len(p) + 1 and p in words_:
            rest = root[len(p):]
            # imperative of a separable verb ('licht … toe', 'leg … uit', 'geef … aan'): a word sharing the first two
            # letters of the verb root and about its length, plus the particle as a separate word
            if any(w[:2] == rest[:2] and abs(len(w) - len(rest)) <= 2 for w in words_ if w != p):
                return True
    return False


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("check_ex_mappings")
    run = load_json(run_dir / "run.json")
    rules = load_bloom_rules(run["subject"])
    method = load_json(run_dir / "11_method_units.json")
    units = {u["unit_id"]: u for u in method["units"]}
    tolerant = method["method"]["text_extraction"] in ("ocr", "mixed")
    data = load_json(run_dir / "18_ex_mappings.json")
    for e in validate_schema(data, "ex_mappings.schema.json"):
        rep.fail("MS1", e)
    links = data["links"]

    for l in links:
        tag = f"{l['criterion_id']} x {l['unit_id']}"
        u = units.get(l["unit_id"])
        if not u or u["kind"] != "deelvraag":
            rep.fail("MS1", f"{tag}: not a sub-question")
            continue
        # MQ2
        if words(l["quote"]) > MAX_QUOTE_WORDS or not quote_in_text(l["quote"], read_text(run_dir, u.get("text_ref")), tolerant)[0]:
            rep.fail("MQ2", f"{tag}: quote not in question text or > {MAX_QUOTE_WORDS} words")
        # MB1
        if l["bloom"] not in BLOOM_ORDER:
            rep.fail("MB1", f"{tag}: bloom {l['bloom']} not a level")
        lv = verb_levels(rules, l.get("bloom_verb"))
        if lv and l["bloom"] not in lv and "volgens tabel" not in (l.get("note") or ""):
            rep.fail("MB1", f"{tag}: verb '{l['bloom_verb']}' is {lv} but bloom {l['bloom']} without note")
        # MB2: the bloom_verb must be the asking verb of the question, not a substitute
        if l.get("bloom_verb") and not verb_in_text(l["bloom_verb"], read_text(run_dir, u.get("text_ref"))):
            rep.warn("MB2", f"{tag}: bloom_verb '{l['bloom_verb']}' not found in the question")
        # MC1
        js = [v for v in l["judges"].values() if v]
        if len(js) == 2:
            exp = "high" if js[0]["bloom"] == js[1]["bloom"] and all(v["quote_valid"] for v in js) else "medium"
        else:
            exp = "low"
        if lv and l["bloom"] not in lv:
            exp = min(exp, "medium", key=CONF.index)
        if l["confidence_judged"] != exp:
            rep.fail("MC1", f"{tag}: confidence_judged {l['confidence_judged']} != computed {exp}")

    if "--verification" in argv:
        ver = load_json(run_dir / argv[argv.index("--verification") + 1])
        for e in validate_schema(ver, "ex_verification.schema.json"):
            rep.fail("MS1", f"verification: {e}")
        idx = {(l["criterion_id"], l["unit_id"]): l for l in links}
        for l in links:
            l["confidence"], l["verifier"] = l["confidence_judged"], None
        applied, resolved = 0, 0
        for v in ver["links"]:
            l = idx.get((v["criterion_id"], v["unit_id"]))
            if not l:
                # a disputed link the repair judge removed is settled; a passed link that is gone is worth a look
                if v["verdict"] == "dispute":
                    resolved += 1
                else:
                    rep.warn("MS1", f"link {v['criterion_id']} x {v['unit_id']} passed by the verifier was removed in repair")
                continue
            verdict = v["verdict"]
            repaired = any(j and j.get("repaired") for j in l["judges"].values())
            if verdict == "dispute" and repaired and v.get("bloom_should_be") in (None, l["bloom"]) and v.get("criterion_should_be") in (None, l["criterion_id"]):
                verdict = "resolved"
                resolved += 1
            l["verifier"] = verdict + (f": {v['reason']}" if v.get("reason") else "")
            adj = v.get("confidence_adjust")
            if adj:
                i = CONF.index(l["confidence"])
                l["confidence"] = CONF[min(2, i + 1)] if adj == "up" else CONF[max(0, i - 1)]
            applied += 1
        save_json(run_dir / "18_ex_mappings.json", data)
        rep.info("MS1", f"applied {applied} verdicts ({resolved} resolved by repair); {len(ver['missing_links'])} missing-link proposals")

    rep.info("MB1", f"{len(links)} exercise links; bloom {dict(Counter(l['bloom'] for l in links))}; "
             f"confidence {dict(Counter(l['confidence'] for l in links))}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
