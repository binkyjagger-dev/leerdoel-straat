#!/usr/bin/env python3
"""E6 — add a run's exams to the subject's exam bank (specs/25 §1–§2).

Usage: bank_add.py <run_dir> [--bank <dir>] [--replace]

Reads run.json (subject, criteria_run), 20_criteria.json, 20_source_units.json, 21_exam_units.json,
24_mappings.json. The bank (default subjects/<subject>/examenbank) is created on first use with a copy of
the criteria; afterwards the run's criteria_run must equal the bank's. A new exam is appended; an existing
exam is replaced only with --replace (the old links file is kept as links/<exam_id>.<date>.json). Other
exams' files are never touched.
"""
from __future__ import annotations

import datetime
import shutil
import sys
from pathlib import Path

from ecommon import ROOT, Report, Units, load_json, save_json, validate_def, validate_schema


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    rep = Report("bank_add")
    run = load_json(run_dir / "run.json")
    subject, criteria_run = run["subject"], run["criteria_run"]
    bank = Path(argv[argv.index("--bank") + 1]) if "--bank" in argv else ROOT / "subjects" / subject / "examenbank"
    replace = "--replace" in argv
    today = datetime.date.today().isoformat()
    units = Units(run_dir)
    links = load_json(run_dir / "24_mappings.json")["links"]

    reg_path = bank / "register.json"
    new_bank = not reg_path.exists()
    if not new_bank:
        reg = load_json(reg_path)
        if reg["criteria_run"] != criteria_run:
            rep.fail("EB1", f"bank is bound to criteria run {reg['criteria_run']}, this run used {criteria_run} "
                            f"(new criteria: /examen --rebuild)")
            rep.print_and_exit()
    else:
        reg = {"subject": subject, "criteria_run": criteria_run, "created_at": today, "exams": []}

    known = {e["exam_id"] for e in reg["exams"]}
    pending: list[tuple[str, dict]] = []  # written only when every exam passes
    for eid, ex in units.exams.items():
        if eid in known and not replace:
            rep.fail("EB2", f"{eid} is already in the bank (use --replace to replace it)")
            continue
        recs = []
        for l in links:
            if l["exam_id"] != eid:
                continue
            sp = units.by_id[l["scorepunt_id"]]
            q = units.by_id[l["question_id"]]
            og = units.by_id[l["opgave_id"]]
            recs.append({"scorepunt_id": l["scorepunt_id"], "question_id": q["unit_id"], "opgave_id": og["unit_id"],
                         "question_number": q["number"], "opgave_number": og["number"], "opgave_title": og.get("title"),
                         "scorepunt_seq": sp["seq"], "scorepunt_kind": sp["scoring"], "points": l["points"],
                         "criterion_id": l["criterion_id"], "group_id": l.get("group_id"),
                         "also_touches": l["also_touches"], "bloom": l["bloom"], "bloom_verb": l.get("bloom_verb"),
                         "quote": l["quote"], "confidence": l["confidence"], "verifier": l["verifier"],
                         "note": l.get("note")})
        recs.sort(key=lambda r: (r["question_number"], r["scorepunt_seq"]))
        lf = {"exam_id": eid, "criteria_run": criteria_run, "run_id": run["run_id"], "scorepunten": recs}
        errs = validate_def(lf, "exam_bank.schema.json", "links_file")
        if errs:
            rep.fail("EB3", f"{eid}: {errs[0]}")
            continue
        if sum(r["points"] for r in recs) != ex["max_score"]:
            rep.fail("EB3", f"{eid}: scorepunten sum to {sum(r['points'] for r in recs)}, max_score {ex['max_score']}")
            continue
        pending.append((eid, lf))
        entry ={"exam_id": eid, "code": ex["code"], "year": ex["year"], "tijdvak": ex["tijdvak"],
                 "level": ex["level"], "n_questions": ex["n_questions"], "max_score": ex["max_score"],
                 "syllabus_note": ex.get("syllabus_note"), "files": ex.get("source_files") or ex["files"],
                 "added_by_run": run["run_id"], "added_at": today}
        reg["exams"] = [e for e in reg["exams"] if e["exam_id"] != eid] + [entry]
        linked = sum(r["points"] for r in recs if r["criterion_id"])
        rep.info("EB2", f"{'replaced' if eid in known else 'added'} {eid}: {len(recs)} scorepunten, "
                        f"{linked}/{ex['max_score']} points linked")
    reg["exams"].sort(key=lambda e: (e["year"], e["tijdvak"], e["exam_id"]))
    for e in validate_schema(reg, "exam_bank.schema.json"):
        rep.fail("EB1", e)
    if rep.failed:
        rep.print_and_exit()  # nothing written
    (bank / "links").mkdir(parents=True, exist_ok=True)
    if new_bank:
        shutil.copy2(run_dir / "20_criteria.json", bank / "criteria.json")
        shutil.copy2(run_dir / "20_source_units.json", bank / "source_units.json")
        rep.info("EB1", f"new bank at {bank} for criteria run {criteria_run}")
    for eid, lf in pending:
        path = bank / "links" / f"{eid}.json"
        if path.exists():
            shutil.copy2(path, bank / "links" / f"{eid}.{today}.json")
        save_json(path, lf)
    save_json(reg_path, reg)
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
