#!/usr/bin/env python3
"""E7 — add a run's merged labels to the exam bank (specs/26 §3.5, §5).

Usage: bank_labels_add.py <run_dir> [--bank <dir>] [--replace]

Reads run.json, 26_labels.json and the bank (register.json, links/<exam_id>.json). Writes
labels/<exam_id>.json per exam of the run, with the same replace rules as bank_add.py: a new exam is added; an
existing labels file is replaced only with --replace (the old one is kept as labels/<exam_id>.<date>.json);
other exams' files are never touched. The exam must already be in the bank (bank_add.py first), the run's
criteria_run must equal the bank's. `combination` and `bloom` are recomputed from the bank's links; a question's
points must equal the sum of its scorepunten in the links, and the labelled points must equal the exam's
max_score. Nothing is written unless every exam passes.
"""
from __future__ import annotations

import datetime
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from lcommon import computed_fields
from ecommon import ROOT, Report, load_json, save_json, validate_def


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("bank_labels_add")
    run = load_json(run_dir / "run.json")
    subject = run["subject"]
    bank = Path(argv[argv.index("--bank") + 1]) if "--bank" in argv else ROOT / "subjects" / subject / "examenbank"
    replace = "--replace" in argv
    today = datetime.date.today().isoformat()
    merged = load_json(run_dir / "26_labels.json")
    if merged["mode"] != "exam":
        rep.fail("BL1", "26_labels.json is not in exam mode")
        rep.print_and_exit()
    reg_path = bank / "register.json"
    if not reg_path.exists():
        rep.fail("BL1", f"no exam bank at {bank} (run bank_add.py first)")
        rep.print_and_exit()
    reg = load_json(reg_path)
    if reg["criteria_run"] != run["criteria_run"]:
        rep.fail("BL1", f"bank is bound to criteria run {reg['criteria_run']}, this run used {run['criteria_run']}")
        rep.print_and_exit()
    exams = {e["exam_id"]: e for e in reg["exams"]}
    by_exam = defaultdict(list)
    for l in merged["labels"]:
        by_exam[l["exam_id"]].append(l)

    pending = []
    for eid, labels in sorted(by_exam.items()):
        if eid not in exams:
            rep.fail("BL1", f"{eid} is not in the bank register (bank_add.py first)")
            continue
        path = bank / "labels" / f"{eid}.json"
        if path.exists() and not replace:
            rep.fail("BL2", f"{eid} already has labels in the bank (use --replace to replace them)")
            continue
        lp = bank / "links" / f"{eid}.json"
        if not lp.exists():
            rep.fail("BL1", f"{eid}: no links file {lp}")
            continue
        links = defaultdict(list)
        for sp in load_json(lp)["scorepunten"]:
            links[sp["question_id"]].append(sp)
        recs, bad = [], False
        for l in sorted(labels, key=lambda x: x["question_number"]):
            sps = links.get(l["question_id"], [])
            if sum(s["points"] for s in sps) != l["points"]:
                rep.fail("BL3", f"{l['question_id']}: {l['points']} points in the units, "
                                f"{sum(s['points'] for s in sps)} in the bank links")
                bad = True
            rec = {k: v for k, v in l.items() if k not in ("disagreements",)}
            rec.update(computed_fields(sps))
            recs.append(rec)
        ex = exams[eid]
        if len(recs) != ex["n_questions"]:
            rep.fail("BL3", f"{eid}: {len(recs)} labelled questions, register has {ex['n_questions']}")
            bad = True
        if sum(r["points"] for r in recs) != ex["max_score"]:
            rep.fail("BL3", f"{eid}: labelled points {sum(r['points'] for r in recs)} != max_score {ex['max_score']}")
            bad = True
        lf = {"exam_id": eid, "criteria_run": reg["criteria_run"], "run_id": run["run_id"], "questions": recs}
        errs = validate_def(lf, "item_labels.schema.json", "bank_file")
        if errs:
            rep.fail("BL3", f"{eid}: {errs[0]}")
            bad = True
        if not bad:
            pending.append((eid, path, lf))
            disputed = sum(1 for r in recs for c in r["confidence"].values() if c == "disputed")
            rep.info("BL2", f"{'replaced' if path.exists() else 'added'} labels {eid}: {len(recs)} questions, "
                            f"{disputed} disputed fields")
    if rep.failed:
        rep.print_and_exit()  # nothing written
    (bank / "labels").mkdir(parents=True, exist_ok=True)
    for eid, path, lf in pending:
        if path.exists():
            shutil.copy2(path, bank / "labels" / f"{eid}.{today}.json")
        save_json(path, lf)
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
