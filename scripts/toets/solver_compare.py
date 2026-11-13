#!/usr/bin/env python3
"""T4 — compare the blind solver's answers with the correctievoorschrift (specs/34 §4, SC).

Usage: solver_compare.py <run_dir> [--opgave <id>]

Per calculation vraag (a vraag with calcs): the final calc (the calc_ref of its last scorepunt that has one, else its
last calc) and the intermediate calcs are matched against the solver's named numbers. A number matches when it
equals the calc value after the cv's rounding (half a unit of the last shown digit; € amounts to the cent).
Status: `match` (final and all intermediates found), `partial` (final found, an intermediate not), `mismatch`
(final not found), `missing` (no solver answer). Explanation vragen list the solver's answer next to the model answer
for the verifier. Ambiguity notes are passed on. Writes 34_solver_compare.json; mismatches are warnings here and
findings for the verifier (V2), not failures of this script.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from calc_check import evaluate
from nlnum import shown_value
from tcommon import Report, load_json, save_json, validate_schema
from toetsrun import ToetsRun, opt


def tolerance(calc: dict) -> float:
    try:
        _, prefix, _, digits = shown_value(calc["shown"])
    except ValueError:
        prefix, digits = "", 6
    d = calc.get("round") if calc.get("round") is not None else digits
    tol = 0.5 * 10 ** (-d)
    return max(tol, 0.005) if prefix else tol


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    rep = Report("solver_compare")
    run = ToetsRun(R)
    out = []
    for oid, it in run.items(opt(argv, "--opgave")).items():
        sp = R / "34_solutions" / f"{oid}.json"
        if not sp.exists():
            rep.warn("SC", f"{oid}: no solver answers (34_solutions/{oid}.json)")
            continue
        sol = load_json(sp)
        for e in validate_schema(sol, "solver_answers.schema.json")[:3]:
            rep.fail("SC", f"{oid}: {e}")
        answers = {a["vraag"]: a for a in sol.get("answers", [])}
        vals, _ = evaluate(it)
        rows = []
        for v in sorted(it["vragen"], key=lambda x: x["number"]):
            a = answers.get(v["number"])
            base = {"vraag_id": v["vraag_id"], "number": v["number"],
                    "confidence": a["confidence"] if a else None, "ambiguity_notes": a["ambiguity_notes"] if a else []}
            if not a:
                rows.append({**base, "status": "missing"})
                rep.warn("SC", f"{v['vraag_id']}: the solver gave no answer")
                continue
            calcs = [c for c in v["cv"]["calc"] if c["name"] in vals]
            if not calcs:
                rows.append({**base, "status": "explanation", "model_answer": v["cv"]["model_answer"], "solver_answer": a["answer_text"]})
                continue
            refs = [s.get("calc_ref") for s in v["cv"]["scorepunten"] if s.get("calc_ref") in vals]
            final = refs[-1] if refs else calcs[-1]["name"]
            nums = [n["value"] for n in a["numbers"]]
            found = {}
            for c in calcs:
                val, tol = vals[c["name"]]["value"], tolerance(c)
                hit = next((n for n in nums if abs(n - val) <= tol + 1e-9), None)
                found[c["name"]] = {"cv": val, "shown": c["shown"], "solver": hit, "match": hit is not None}
            if not found[final]["match"]:
                status = "mismatch"
            elif all(f["match"] for f in found.values()):
                status = "match"
            else:
                status = "partial"
            rows.append({**base, "status": status, "final": final, "calcs": found, "solver_numbers": a["numbers"],
                         "solver_answer": a["answer_text"]})
            if status != "match":
                got = ", ".join("%s %g" % (n["label"], n["value"]) for n in a["numbers"]) or "geen getallen"
                rep.warn("SC", f"{v['vraag_id']}: {status} — final {final} cv {found[final]['shown']}, solver {got}")
            for note in a["ambiguity_notes"]:
                rep.warn("SC", f"{v['vraag_id']}: solver ambiguity: {note}")
        out.append({"opgave_id": oid, "vragen": rows, "exam_example_errors": sol.get("exam_example_errors", [])})
    summary = dict(Counter(r["status"] for o in out for r in o["vragen"]))
    save_json(R / "34_solver_compare.json", {"opgaven": out, "summary": summary})
    rep.info("SC", f"{summary}")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
