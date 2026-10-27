#!/usr/bin/env python3
"""Validate 21_exam_units.json (specs/21 §6, checks EU1–EU8).

Usage: validate_exam.py <run_dir>
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import Report, load_json, validate_schema  # noqa: E402


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("validate_exam")
    data = load_json(run_dir / "21_exam_units.json")
    for e in validate_schema(data, "exam_units.schema.json"):
        rep.fail("EU1", e)
    if rep.failed:
        rep.print_and_exit()

    units = data["units"]
    by_id = {}
    for uid, n in Counter(u["unit_id"] for u in units).items():
        if n > 1:
            rep.fail("EU1", f"duplicate unit_id {uid}")
    for u in units:
        by_id[u["unit_id"]] = u
        for ref in ("text_ref", "cv_ref", "formula_ref"):
            if u.get(ref) and not (run_dir / u[ref]).exists():
                rep.fail("EU1", f"{u['unit_id']}: {ref} {u[ref]} missing")

    qs_by_exam: dict[str, list[dict]] = defaultdict(list)
    sp_by_q: dict[str, list[dict]] = defaultdict(list)
    q_by_opgave: dict[str, list[dict]] = defaultdict(list)
    for u in units:
        if u["kind"] == "question":
            qs_by_exam[u["exam_id"]].append(u)
            q_by_opgave[u["opgave_id"]].append(u)
            if u["opgave_id"] not in by_id or by_id[u["opgave_id"]]["kind"] != "opgave":
                rep.fail("EU6", f"{u['unit_id']}: opgave {u['opgave_id']} missing")
        elif u["kind"] == "scorepunt":
            sp_by_q[u["question_id"]].append(u)
            if u["question_id"] not in by_id:
                rep.fail("EU1", f"{u['unit_id']}: question {u['question_id']} missing")

    for ex in data["exams"]:
        eid = ex["exam_id"]
        qs = sorted(qs_by_exam[eid], key=lambda q: q["number"])
        nums = [q["number"] for q in qs]
        if ex["n_questions"] is None or ex["max_score"] is None:
            rep.fail("EU2", f"{eid}: header counts missing")
            continue
        if len(qs) != ex["n_questions"] or nums != list(range(1, ex["n_questions"] + 1)):
            missing = sorted(set(range(1, ex["n_questions"] + 1)) - set(nums))
            rep.fail("EU2", f"{eid}: {len(qs)} questions parsed, header says {ex['n_questions']}; missing {missing}")
        total = sum(q["points"] for q in qs)
        if total != ex["max_score"]:
            rep.fail("EU3", f"{eid}: question points sum to {total}, header max_score {ex['max_score']}")
        for q in qs:
            if q["cv_max"] != q["points"]:
                rep.fail("EU4", f"{q['unit_id']}: {q['points']}p in opgaven, maximumscore {q['cv_max']} in correctievoorschrift")
            sp = sp_by_q.get(q["unit_id"], [])
            if sum(s["points"] for s in sp) != q["cv_max"]:
                rep.fail("EU5", f"{q['unit_id']}: scorepunten sum to {sum(s['points'] for s in sp)}, maximumscore {q['cv_max']}")
            if [s["seq"] for s in sorted(sp, key=lambda s: s["seq"])] != list(range(1, len(sp) + 1)):
                rep.fail("EU5", f"{q['unit_id']}: scorepunt seq not 1..n")
        bron_files = {int(m.group(1)) for p in (run_dir / "text").glob(f"{eid}-bron*.txt")
                      if (m := re.search(r"-bron(\d+)\.txt$", p.name))}
        for u in units:
            if u["exam_id"] == eid and u["kind"] in ("opgave", "question"):
                for n in u.get("sources", []):
                    if n not in bron_files:
                        rep.warn("EU7", f"{u['unit_id']}: informatiebron {n} not found in the bijlage")
        sps = [s for q in qs for s in sp_by_q.get(q["unit_id"], [])]
        rep.info("EU2", f"{eid}: {len(qs)} questions, {ex['max_score']} p, {len(sps)} scorepunten "
                        f"{dict(Counter(s['scoring'] for s in sps))}; extraction={ex['text_extraction']}")

    for u in units:
        if u["kind"] == "opgave" and not q_by_opgave.get(u["unit_id"]):
            rep.fail("EU6", f"{u['unit_id']}: opgave without questions")
    for x in data["parse_issues"]:
        rep.fail("EU8", f"{x['exam_id']} {x.get('unit_id') or ''}: {x['issue']}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
