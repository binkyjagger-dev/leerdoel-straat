#!/usr/bin/env python3
"""M7 — candidate criteria per sub-question (specs/12 §6.1).

Usage: ex_candidates.py <run_dir> [--top 8] [--min 3]

Reads run.json, 10_criteria.json, 11_method_units.json (+ text/), 14_mappings.json (part A),
12_candidates.json (scope_criteria). Part B scope = every paragraph of the ingested chapters
(run.json `ex_scope_paragraphs` overrides). Writes 17_ex_candidates.json. No LLM call.
"""
from __future__ import annotations

import math
import re
import sys
from collections import Counter
from pathlib import Path

from mcommon import load_json, read_text, save_json, stems, validate_schema

TAUGHT = ("leert", "herhaalt", "oefent")
ASK = re.compile(r"^\s*(?:[a-z]|\d+)[.)]\s", re.M)


def ask_part(text: str) -> str:
    """The sub-question's own ask: text from its last letter/number marker on (the shared stem comes before)."""
    marks = list(ASK.finditer(text))
    return text[marks[-1].start():] if marks else text


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    opt = lambda f, d: int(argv[argv.index(f) + 1]) if f in argv else d
    top, mn = opt("--top", 8), opt("--min", 3)

    run = load_json(run_dir / "run.json")
    method = load_json(run_dir / "11_method_units.json")
    units = {u["unit_id"]: u for u in method["units"]}
    order = {u["unit_id"]: u.get("order") or 0 for u in method["units"]}
    paras = [u["unit_id"] for u in method["units"] if u["kind"] == "paragraaf"]
    scope = run.get("ex_scope_paragraphs") or paras
    cand_a = load_json(run_dir / "12_candidates.json")
    scope_crit = set(cand_a.get("scope_criteria") or [c["criterion_id"] for c in cand_a["per_criterion"]])
    links = load_json(run_dir / "14_mappings.json")["links"]

    crit_terms = {}
    for g in load_json(run_dir / "10_criteria.json")["groups"]:
        for c in g["criteria"]:
            crit_terms[c["criterion_id"]] = stems(c["text_expert"]) | stems(g["goal"]["text_expert"])
    # idf over criteria, so generic words ("prijs", "vraag") weigh less than specific ones
    df = Counter(t for ts in crit_terms.values() for t in ts)
    N = max(len(crit_terms), 1)
    idf = {t: math.log((N + 1) / (d + 1)) + 1 for t, d in df.items()}

    taught = {}  # criterion -> list of paragraphs where it is leert/herhaalt/oefent
    for l in links:
        if l["gradation"] in TAUGHT:
            taught.setdefault(l["criterion_id"], []).append(l["unit_id"])
    gap_crit = [c for c in scope_crit if c not in taught]

    def para_of(uid: str) -> str:
        u = units[uid]
        while u["kind"] != "paragraaf":
            u = units[u["parent_id"]]
        return u["unit_id"]

    out = []
    for u in method["units"]:
        if u["kind"] != "deelvraag":
            continue
        pid = para_of(u["unit_id"])
        if pid not in scope:
            continue
        qtext = read_text(run_dir, u.get("text_ref"))
        terms = stems(qtext)
        focus = stems(ask_part(qtext) + "\n" + ask_part(read_text(run_dir, u.get("answer_ref"))))
        pool = {}
        for cid, ps in taught.items():
            earlier = [p for p in ps if order.get(p, 0) <= order[pid]]
            if earlier:
                pool[cid] = ("own", pid) if pid in earlier else ("earlier", max(earlier, key=lambda p: order[p]))
        for cid in gap_crit:
            pool.setdefault(cid, ("gap", None))
        scored = []
        for cid, (src, where) in pool.items():
            # stem terms count once, the ask and its answer twice more
            s = sum(idf.get(t, 1.0) for t in crit_terms[cid] & terms) + 2 * sum(idf.get(t, 1.0) for t in crit_terms[cid] & focus)
            if s > 0 and src == "own":
                s += 2.0
            scored.append((round(s, 2), cid, src, where))
        scored.sort(key=lambda x: (-x[0], x[1]))
        chosen = [x for x in scored[:top] if x[0] > 0]
        if 0 < len(chosen) < mn:
            chosen = [x for x in scored[:mn] if x[0] > 0]
        out.append({"unit_id": u["unit_id"], "paragraph_id": pid,
                    "candidates": [{"criterion_id": cid, "score": s, "source": src, "taught_in": where} for s, cid, src, where in chosen]})

    res = {"scope_paragraphs": [p for p in paras if p in scope], "per_subquestion": out}
    errs = validate_schema(res, "ex_candidates.schema.json")
    if errs:
        sys.exit("invalid ex candidates: " + "; ".join(errs[:3]))
    save_json(run_dir / "17_ex_candidates.json", res)
    empty = sum(1 for x in out if not x["candidates"])
    print(f"[ex_candidates] {len(out)} sub-questions in {len(res['scope_paragraphs'])} paragraphs; "
          f"{sum(len(x['candidates']) for x in out)} candidate pairs; {empty} without candidates; "
          f"{len(gap_crit)} part-A gap criteria in the pool")


if __name__ == "__main__":
    main(sys.argv)
