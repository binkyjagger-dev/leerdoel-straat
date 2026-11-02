#!/usr/bin/env python3
"""E2 — candidate criteria per scorepunt (specs/23 §3 E2).

Usage: exam_candidates.py <run_dir> [--top 8] [--min 3]

Reads 20_criteria.json and 21_exam_units.json (+ text/). Every criterion is a candidate for every
scorepunt; ranked by term overlap (idf over criteria) between the criterion (expert text + goal +
concepts) and the scorepunt text (x3), the question's ask (x2), and its context, the opgave text and
the informatiebronnen it names (x1). Writes 22_candidates.json. No LLM call.
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

from ecommon import Units, ask_of, criteria_index, load_json, read_text, save_json, validate_schema
from mcommon import glossary_stems


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    opt = lambda f, d: int(argv[argv.index(f) + 1]) if f in argv else d
    top, mn = opt("--top", 8), opt("--min", 3)

    units = Units(run_dir)
    stems = glossary_stems(load_json(run_dir / "run.json")["subject"], set(units.exams))  # specs/06 §8
    crit = criteria_index(load_json(run_dir / "20_criteria.json"))
    terms = {cid: stems(c["text_expert"]) | stems(c["goal_expert"]) | stems(" ".join(c["concepts"]))
             for cid, c in crit.items()}
    df = Counter(t for ts in terms.values() for t in ts)
    n = max(len(terms), 1)
    idf = {t: math.log((n + 1) / (d + 1)) + 1 for t, d in df.items()}

    def bron_text(exam_id: str, nums: list[int]) -> str:
        return "\n".join(read_text(run_dir, f"text/{exam_id}-bron{k}.txt") for k in nums
                         if (run_dir / f"text/{exam_id}-bron{k}.txt").exists())

    out = []
    for sp in units.scorepunten:
        q = units.by_id[sp["question_id"]]
        og = units.by_id[q["opgave_id"]]
        qtext = units.question_text(q["unit_id"])
        heavy = stems(sp["text"])
        mid = stems(ask_of(qtext))
        light = stems(qtext) | stems(read_text(run_dir, og.get("text_ref"))) | \
            stems(bron_text(sp["exam_id"], sorted(set(q["sources"]) | set(og["sources"]))))
        scored = []
        for cid, ts in terms.items():
            s = (3 * sum(idf[t] for t in ts & heavy) + 2 * sum(idf[t] for t in ts & mid)
                 + sum(idf[t] for t in ts & light))
            if s > 0:
                scored.append((round(s, 2), cid))
        scored.sort(key=lambda x: (-x[0], x[1]))
        chosen = scored[:max(top, 0)] if scored else []
        if 0 < len(chosen) < mn:
            chosen = scored[:mn]
        out.append({"scorepunt_id": sp["unit_id"], "question_id": q["unit_id"], "opgave_id": og["unit_id"],
                    "candidates": [{"criterion_id": cid, "score": s} for s, cid in chosen]})

    res = {"per_scorepunt": out}
    errs = validate_schema(res, "exam_candidates.schema.json")
    if errs:
        sys.exit("invalid exam candidates: " + "; ".join(errs[:3]))
    save_json(run_dir / "22_candidates.json", res)
    empty = sum(1 for x in out if not x["candidates"])
    print(f"[exam_candidates] {len(out)} scorepunten in {len(units.exams)} exams; "
          f"{sum(len(x['candidates']) for x in out)} candidate pairs; {empty} without candidates; "
          f"{len(crit)} criteria")


if __name__ == "__main__":
    main(sys.argv)
