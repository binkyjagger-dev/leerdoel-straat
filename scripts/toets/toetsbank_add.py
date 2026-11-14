#!/usr/bin/env python3
"""T6 — add a finished toets to the subject's toetsbank (specs/35 §4); T0 helper for the context history.

Usage:
  toetsbank_add.py <run_dir> [--toetsbank <dir>] [--replace] [--subjects <dir>]
  toetsbank_add.py --history <run_dir> [--toetsbank <dir>] [--months 24] [--subjects <dir>]

Add: reads run.json and output/toets.json (export_toets.py). The toetsbank (default subjects/<s>/toetsbank) is
created on first use, bound to the run's criteria_run; afterwards the criteria_run must be equal (a new criteria run
needs a new toetsbank — the one destructive step, done by hand after asking the teacher). A new toets_id is appended;
an existing one is replaced only with --replace (the old toetsen/<id>.json is kept as toetsen/<id>.<date>.json and
its contexts are replaced). Writes register.json, toetsen/<toets_id>.json, contexts.json (one entry per opgave
that is not reused) and rebuilds output/overzicht.md (per leerdoel and criterion the vragen that test it, per pattern
the count). The toetsbank holds no exam text. Nothing is written when a check fails.
History: writes <run_dir>/30_context_history.json = contexts.json filtered to the last <months> months (default 24,
specs/35 §4), relative to today.
"""
from __future__ import annotations

import datetime
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from tcommon import ROOT, Report, load_json, pattern_codes, save_json, validate_def, validate_schema
from toetsrun import opt


def bank_dir(argv: list[str], subject: str) -> Path:
    if opt(argv, "--toetsbank"):
        return Path(opt(argv, "--toetsbank"))
    subjects = Path(opt(argv, "--subjects")) if opt(argv, "--subjects") else ROOT / "subjects"
    return subjects / subject / "toetsbank"


def history(argv: list[str]) -> None:
    R = Path(argv[argv.index("--history") + 1])
    run = load_json(R / "run.json")
    tb = bank_dir(argv, run["subject"])
    months = int(opt(argv, "--months") or 24)
    today = datetime.date.today()
    y, m = today.year, today.month - months
    while m <= 0:
        y, m = y - 1, m + 12
    cutoff = datetime.date(y, m, min(today.day, 28)).isoformat()
    ctx = load_json(tb / "contexts.json")["contexts"] if (tb / "contexts.json").exists() else []
    keep = [c for c in ctx if c["date"] >= cutoff]
    save_json(R / "30_context_history.json", {"contexts": keep, "since": cutoff, "months": months})
    print(f"[toetsbank_add] history: {len(keep)} of {len(ctx)} contexts since {cutoff} -> {R / '30_context_history.json'}")


def overzicht(tb: Path, reg: dict, criteria: dict | None) -> str:
    per_crit, per_pat = defaultdict(list), defaultdict(int)
    for t in reg["toetsen"]:
        tf = tb / "toetsen" / f"{t['toets_id']}.json"
        if not tf.exists():
            continue
        for og in load_json(tf)["opgaven"]:
            for v in og["vragen"]:
                for c in pattern_codes(v.get("pattern")):
                    per_pat[c] += 1
                for s in v["scorepunten"]:
                    per_crit[s["criterion_id"]].append(f"{t['toets_id']} · {og['opgave_id']} {og['title']} · vraag "
                                                       f"{v.get('number', '?')} · {s['points']} p")
    L = [f"# Toetsbank — {reg['subject']}", "", f"Criteriaversie: `{reg['criteria_run']}` · {len(reg['toetsen'])} toets(en).", "",
         "*Gebouwd door `scripts/toets/toetsbank_add.py`; niet met de hand bewerken.*", "", "## Toetsen", "",
         "| toets | titel | niveau | punten | opgaven | vragen | datum |", "|---|---|---|---|---|---|---|"]
    L += [f"| {t['toets_id']} | {t['title']} | {t['level']} | {t['max_score']} | {t['n_opgaven']} | {t['n_vragen']} | {t['created_at']} |"
          for t in reg["toetsen"]]
    L += ["", "## Per leerdoel en criterium", ""]
    groups = (criteria or {}).get("groups") or []
    seen = set()
    for g in groups:
        rows = [(c["criterion_id"], per_crit.get(c["criterion_id"], [])) for c in g["criteria"]]
        if not any(r[1] for r in rows):
            continue
        L.append(f"**{g['group_id']}** {g['goal'].get('text_student') or ''}")
        for cid, hits in rows:
            seen.add(cid)
            L.append(f"- {cid}: " + ("; ".join(hits) if hits else "niet getoetst"))
        L.append("")
    for cid in sorted(set(per_crit) - seen):
        L.append(f"- {cid}: {'; '.join(per_crit[cid])}")
    L += ["", "## Per patroon", "", "| patroon | vragen |", "|---|---|"] + [f"| {c} | {n} |" for c, n in sorted(per_pat.items())]
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> None:
    if "--history" in argv:
        history(argv)
        return
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    rep = Report("toetsbank_add")
    run = load_json(R / "run.json")
    rec = load_json(R / "output" / "toets.json")
    for e in validate_def(rec, "toetsbank.schema.json", "toets_file")[:5]:
        rep.fail("TB1", f"toets.json: {e}")
    tb = bank_dir(argv, run["subject"])
    today = datetime.date.today().isoformat()
    reg_path = tb / "register.json"
    new = not reg_path.exists()
    reg = load_json(reg_path) if not new else {"subject": run["subject"], "criteria_run": run["criteria_run"],
                                                "created_at": today, "toetsen": []}
    if reg["criteria_run"] != rec["criteria_run"]:
        rep.fail("TB1", f"toetsbank bound to criteria run {reg['criteria_run']}, the toets to {rec['criteria_run']} "
                        f"(new criteria: a new toetsbank; move the old one to toetsbank.<criteria_run>/ after asking the teacher)")
    tid = rec["toets_id"]
    known = any(t["toets_id"] == tid for t in reg["toetsen"])
    if known and "--replace" not in argv:
        rep.fail("TB2", f"{tid} is already in the toetsbank (use --replace to replace it)")
    if rep.failed:
        rep.print_and_exit()  # nothing written
    n_vragen = sum(len(o["vragen"]) for o in rec["opgaven"])
    entry = {"toets_id": tid, "title": rec["title"], "level": rec.get("level") or "", "run_id": rec.get("run_id") or run["run_id"],
             "created_at": rec.get("created_at") or today, "max_score": rec["max_score"], "n_opgaven": len(rec["opgaven"]),
             "n_vragen": n_vragen, "reference": rec.get("reference")}
    reg["toetsen"] = [t for t in reg["toetsen"] if t["toets_id"] != tid] + [entry]
    for e in validate_schema(reg, "toetsbank.schema.json")[:5]:
        rep.fail("TB1", f"register: {e}")
    ctx_path = tb / "contexts.json"
    ctx = load_json(ctx_path) if ctx_path.exists() else {"contexts": []}
    ctx["contexts"] = [c for c in ctx["contexts"] if c["toets_id"] != tid] + [
        {"toets_id": tid, "opgave_id": o["opgave_id"], "title": o["title"], "context_tags": o.get("context_tags", []),
         "level": rec.get("level") or "", "date": entry["created_at"]} for o in rec["opgaven"] if not o.get("reused_from")]
    for e in validate_def(ctx, "toetsbank.schema.json", "contexts")[:5]:
        rep.fail("TB1", f"contexts: {e}")
    if rep.failed:
        rep.print_and_exit()
    (tb / "toetsen").mkdir(parents=True, exist_ok=True)
    tf = tb / "toetsen" / f"{tid}.json"
    if tf.exists():
        shutil.copy2(tf, tb / "toetsen" / f"{tid}.{today}.json")
    save_json(tf, rec)
    save_json(reg_path, reg)
    save_json(ctx_path, ctx)
    crit = R / "30_criteria.json"
    (tb / "output").mkdir(exist_ok=True)
    (tb / "output" / "overzicht.md").write_text(overzicht(tb, reg, load_json(crit) if crit.exists() else None), encoding="utf-8")
    rep.info("TB2", f"{'replaced' if known else 'added'} {tid}: {len(rec['opgaven'])} opgaven, {n_vragen} vragen, "
                    f"{rec['max_score']} p; {len(ctx['contexts'])} contexts in the history" + ("; new toetsbank" if new else ""))
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
