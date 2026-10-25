#!/usr/bin/env python3
"""M2 — candidate paragraphs per criterion and candidate criteria per paragraph (specs/13 §2 M2).

Usage: candidates.py <run_dir> [--top 6] [--min 3] [--reverse-top 10]

Reads 10_criteria.json (groups from /generate), 11_method_units.json (+ text/), optional
subjects/<subject>/glossary.json. Scores = concept overlap (weighted) + TF-IDF cosine on text.
Writes 12_candidates.json. No LLM call.
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from mcommon import ROOT, load_json, read_text, save_json, stems, validate_schema


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    opt = lambda f, d: int(argv[argv.index(f) + 1]) if f in argv else d
    top, mn, rtop = opt("--top", 6), opt("--min", 3), opt("--reverse-top", 10)

    run = load_json(run_dir / "run.json")
    crit_src = load_json(run_dir / "10_criteria.json")
    method = load_json(run_dir / "11_method_units.json")
    scope = set(run.get("scope_paragraphs") or [u["unit_id"] for u in method["units"] if u["kind"] == "paragraaf"])
    glossary = {}
    gp = ROOT / "subjects" / run["subject"] / "glossary.json"
    if gp.exists():
        g = load_json(gp)
        for term, syns in (g.get("synonyms") or {}).items():
            for s in syns:
                glossary[s.lower()] = term.lower()

    def canon(text: str) -> set[str]:
        out = set()
        for t in stems(text):
            out.add(glossary.get(t, t))
        return out

    # criteria
    criteria = []
    for g in crit_src["groups"]:
        gconcepts = set()
        for c in g.get("concepts") or []:
            gconcepts |= canon(c)
        for c in g["criteria"]:
            criteria.append({
                "criterion_id": c["criterion_id"], "group_id": g["group_id"],
                "concepts": gconcepts,
                "terms": canon(c["text_expert"]) | canon(g["goal"]["text_expert"]),
            })

    # paragraphs
    paras = []
    for u in method["units"]:
        if u["kind"] != "paragraaf" or u["unit_id"] not in scope:
            continue
        text = read_text(run_dir, u.get("text_ref"))
        pconcepts = set()
        for c in u.get("concepts") or []:
            pconcepts |= canon(c)
        paras.append({"unit_id": u["unit_id"], "concepts": pconcepts, "terms": canon(text),
                      "tf": Counter(glossary.get(t, t) for t in stems(text)) , "title": canon(u.get("title") or "")})

    # idf over paragraphs
    df = Counter()
    for p in paras:
        for t in p["terms"]:
            df[t] += 1
    N = max(len(paras), 1)
    idf = {t: math.log((N + 1) / (d + 1)) + 1 for t, d in df.items()}

    def score(c, p) -> tuple[float, str]:
        s = 0.0
        why = []
        cc = c["concepts"] & (p["concepts"] | p["title"])
        if cc:
            s += 3.0 * len(cc); why.append(f"concept↔concept/title {sorted(cc)[:4]}")
        ct = (c["concepts"] & p["terms"]) - cc
        if ct:
            s += 1.5 * len(ct); why.append(f"concept in text {sorted(ct)[:4]}")
        tt = (c["terms"] & p["terms"]) - cc - ct
        if tt:
            w = sum(idf.get(t, 1.0) for t in tt)
            s += 0.4 * w; why.append(f"terms {sorted(tt, key=lambda t: -idf.get(t,1))[:5]}")
        return round(s, 2), "; ".join(why)

    crit_units = set(run.get("scope_criteria") or [g["unit_id"] for g in crit_src["groups"]])
    scope_crit = [c["criterion_id"] for g in crit_src["groups"] if g["unit_id"] in crit_units for c in g["criteria"]]
    in_scope = set(scope_crit)
    per_crit, per_para = [], defaultdict(list)
    for c in criteria:
        scored = sorted(((score(c, p), p["unit_id"]) for p in paras), key=lambda x: -x[0][0])
        chosen = [x for x in scored[:top] if x[0][0] > 0]
        if len(chosen) < mn:
            chosen = scored[:mn]
        if c["criterion_id"] in in_scope:
            per_crit.append({"criterion_id": c["criterion_id"],
                             "candidates": [{"unit_id": uid, "score": sc, "why": why} for (sc, why), uid in chosen]})
        for (sc, _), uid in scored:
            if sc > 0:
                per_para[uid].append({"criterion_id": c["criterion_id"], "score": sc})
    per_para_out = [{"unit_id": p["unit_id"], "criteria": sorted(per_para.get(p["unit_id"], []), key=lambda x: -x["score"])[:rtop]} for p in paras]
    out = {"scope_paragraphs": sorted(scope), "scope_criteria": scope_crit, "per_criterion": per_crit, "per_paragraph": per_para_out}
    errs = validate_schema(out, "candidates.schema.json")
    if errs:
        sys.exit("invalid candidates: " + "; ".join(errs))
    save_json(run_dir / "12_candidates.json", out)
    n_links = sum(len(c["candidates"]) for c in per_crit)
    print(f"[candidates] {len(criteria)} criteria x {len(paras)} paragraphs -> {n_links} candidate pairs (top {top}, min {mn})")


if __name__ == "__main__":
    main(sys.argv)
