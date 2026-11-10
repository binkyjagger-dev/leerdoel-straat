#!/usr/bin/env python3
"""Extend a finished /koppel run with new chapters of the same method (specs/13 §5).

Usage:
  koppel_extend.py prepare <run_dir> <prev_run_dir>   X0: new run R from finished run P (P untouched)
  koppel_extend.py merge-units <run_dir>              X1b: 11_method_units.prev + .new -> 11_method_units.json
  koppel_extend.py todo <run_dir>                     X2: 12_extend_todo.json (new paragraphs, delta pairs, open pairs)
  koppel_extend.py merge-verification <run_dir> [--part A|B]
                                                      X5/X6: <prev> + <ext> -> 15_verification.json (A)
                                                      or 19_ex_verification.json (B)

Invariant: every candidate pair (paragraph x criterion) has a judgement of judge A and of judge B; P's
judgements are reused, only the missing pairs are judged in R.
"""
from __future__ import annotations

import datetime
import glob
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from mcommon import Report, load_json, save_json, validate_schema

RUN_FIELDS = ("subject", "method_id", "from_run", "chapters", "part", "max_repair_rounds", "judge_batch",
              "scope_criteria", "scope_exclude_groups", "scope_note", "ex_scope_paragraphs", "ex_scope_note",
              "verb_level_exceptions")
COPY_DIRS = ("text", "input", "13_judgements.A", "13_judgements.B", "13_judgements.R",
             "18_ex_judgements.A", "18_ex_judgements.B", "18_ex_judgements.R")
RENAME = {"11_method_units.json": "11_method_units.prev.json",
          "15_verification.json": "15_verification.prev.json",
          "19_ex_verification.json": "19_ex_verification.prev.json"}
LIST_KEYS = ("links", "missing_links", "gradation_findings", "findings", "proposed_decisions")


def prepare(run_dir: Path, prev: Path, rep: Report) -> None:
    prun = load_json(prev / "run.json")
    if prun.get("status") != "done":
        rep.fail("X0", f"{prev.name} is not finished (status {prun.get('status')})")
        return
    if (run_dir / "11_method_units.prev.json").exists():
        rep.fail("X0", f"{run_dir} is already prepared")
        return
    run_dir.mkdir(parents=True, exist_ok=True)
    for d in COPY_DIRS:
        if (prev / d).exists():
            shutil.copytree(prev / d, run_dir / d, dirs_exist_ok=True)
    shutil.copy2(prev / "10_criteria.json", run_dir / "10_criteria.json")
    for f in ("11_ingest_notes.md", "16_teacher_review.json"):  # ingest appends to the notes; review: specs/14 §5.1
        if (prev / f).exists():
            shutil.copy2(prev / f, run_dir / f)
    for src, dst in RENAME.items():
        if (prev / src).exists():
            shutil.copy2(prev / src, run_dir / dst)
    (run_dir / "input" / "ext").mkdir(parents=True, exist_ok=True)
    run = {"run_id": run_dir.name, **{k: prun[k] for k in RUN_FIELDS if k in prun},
           "scope_paragraphs_prev": prun.get("scope_paragraphs", []),
           "extend": {"from_run_id": prun["run_id"]}, "status": "running",
           "started_at": datetime.datetime.now().isoformat(timespec="seconds")}
    save_json(run_dir / "run.json", run)
    njudged = sum(len(glob.glob(str(run_dir / f"13_judgements.{j}" / "*.json"))) for j in "ABR")
    rep.info("X0", f"prepared {run_dir.name} from {prun['run_id']}: {njudged} judgement files, part {prun.get('part')}; "
                   f"put the new book files in {run_dir / 'input' / 'ext'}")


def para_key(code: str) -> tuple:
    nums = re.findall(r"\d+", code or "")
    if not nums:
        raise ValueError(code)
    return tuple(int(n) for n in nums)


def merge_units(run_dir: Path, rep: Report) -> None:
    prev = load_json(run_dir / "11_method_units.prev.json")
    new = load_json(run_dir / "11_method_units.new.json")
    for e in validate_schema(new, "method_units.schema.json")[:5]:
        rep.fail("X1b", f"11_method_units.new.json: {e}")
    old_ids = {u["unit_id"] for u in prev["units"]}
    clash = sorted(old_ids & {u["unit_id"] for u in new["units"]})
    if clash:
        rep.fail("X1b", f"unit ids in both prev and new: {clash[:5]}")
    if rep.failed:
        return
    units = prev["units"] + new["units"]
    paras = [u for u in units if u["kind"] == "paragraaf"]
    try:
        paras.sort(key=lambda u: para_key(u.get("code")))
    except ValueError as e:
        rep.fail("X1b", f"paragraph code {e} has no number; declare the book order in the method profile")
        return
    for i, u in enumerate(paras, start=1):
        u["order"] = i
    method = dict(prev["method"])
    method["files"] = list(dict.fromkeys(prev["method"]["files"] + new["method"]["files"]))
    if new["method"]["text_extraction"] != prev["method"]["text_extraction"]:
        method["text_extraction"] = "mixed"
    method["ingested_at"] = new["method"].get("ingested_at") or method.get("ingested_at")
    save_json(run_dir / "11_method_units.json", {"method": method, "units": units})

    run = load_json(run_dir / "run.json")
    new_paras = [u["unit_id"] for u in new["units"] if u["kind"] == "paragraaf"]
    run["scope_paragraphs"] = list(dict.fromkeys(run.get("scope_paragraphs_prev", []) + new_paras))
    if "ex_scope_paragraphs" in run:
        run["ex_scope_paragraphs"] = list(dict.fromkeys(run["ex_scope_paragraphs"] + new_paras))
    run["extend"]["new_paragraphs"] = new_paras
    run["extend"]["new_subquestions"] = [u["unit_id"] for u in new["units"] if u["kind"] == "deelvraag"]
    save_json(run_dir / "run.json", run)
    moved = [u["unit_id"] for u in paras if u["unit_id"] in old_ids and u["order"] !=
             next(x.get("order") for x in prev["units"] if x["unit_id"] == u["unit_id"])]
    rep.info("X1b", f"{len(prev['units'])} + {len(new['units'])} units; {len(new_paras)} new paragraphs; "
                    f"{len(moved)} old paragraphs got a new order number")


def judged(run_dir: Path, j: str) -> set[tuple[str, str]]:
    out = set()
    for f in glob.glob(str(run_dir / f"13_judgements.{j}" / "*.json")):
        d = load_json(f)
        out |= {(jd["criterion_id"], d["unit_id"]) for jd in d["judgements"]}
    return out


def todo(run_dir: Path, rep: Report) -> None:
    run = load_json(run_dir / "run.json")
    cand = load_json(run_dir / "12_candidates.json")
    union = defaultdict(set)
    for p in cand["per_paragraph"]:
        union[p["unit_id"]] |= {c["criterion_id"] for c in p["criteria"]}
    for pc in cand["per_criterion"]:
        for c in pc["candidates"]:
            union[c["unit_id"]].add(pc["criterion_id"])
    a, b = judged(run_dir, "A"), judged(run_dir, "B")
    new_paras = run["extend"].get("new_paragraphs", [])
    # delta is cumulative: X5 and X7 read it, so a rerun after X3 must keep the pairs judged since; open = still to judge
    delta = {uid: set(crits) for uid, crits in run["extend"].get("delta", {}).items()}
    open_pairs = {}
    for uid, crits in sorted(union.items()):
        if uid in new_paras:
            continue
        missing = sorted(c for c in crits if (c, uid) not in a or (c, uid) not in b)
        if missing:
            open_pairs[uid] = missing
            delta.setdefault(uid, set()).update(missing)
    delta = {uid: sorted(delta[uid]) for uid in sorted(delta)}
    out = {"new_paragraphs": new_paras, "delta": delta, "open": open_pairs}
    save_json(run_dir / "12_extend_todo.json", out)
    run["extend"]["delta"] = delta
    save_json(run_dir / "run.json", run)
    rep.info("X2", f"{len(new_paras)} new paragraphs to judge fully; {sum(len(v) for v in delta.values())} delta pairs "
                   f"on {len(delta)} old paragraphs; {sum(len(v) for v in open_pairs.values())} still open")


def merge_verification(run_dir: Path, part: str, rep: Report) -> None:
    base, schema = ("15_verification", "mapping_verification.schema.json") if part == "A" else \
                   ("19_ex_verification", "ex_verification.schema.json")
    prev_p, ext_p = run_dir / f"{base}.prev.json", run_dir / f"{base}.ext.json"
    if not prev_p.exists() and not ext_p.exists():
        rep.fail("X5", f"neither {prev_p.name} nor {ext_p.name} exists")
        return
    prev = load_json(prev_p) if prev_p.exists() else {}
    ext = load_json(ext_p) if ext_p.exists() else {}
    out = {k: v for k, v in (prev or ext).items() if k not in LIST_KEYS and k != "sample"}
    for k in LIST_KEYS:
        if k in prev or k in ext:
            out[k] = prev.get(k, []) + ext.get(k, [])
    out["sample"] = {"prev": prev.get("sample"), "ext": ext.get("sample")}
    for e in validate_schema(out, schema)[:5]:
        rep.fail("X5", e)
    save_json(run_dir / f"{base}.json", out)
    rep.info("X5", f"{base}.json: {len(prev.get('links', []))} prev + {len(ext.get('links', []))} ext verdicts, "
                   f"{len(out.get('missing_links', []))} missing-link proposals")


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    cmd, run_dir = argv[1], Path(argv[2])
    rep = Report(f"koppel_extend {cmd}")
    if cmd == "prepare" and len(argv) >= 4:
        prepare(run_dir, Path(argv[3]), rep)
    elif cmd == "merge-units":
        merge_units(run_dir, rep)
    elif cmd == "todo":
        todo(run_dir, rep)
    elif cmd == "merge-verification":
        merge_verification(run_dir, argv[argv.index("--part") + 1] if "--part" in argv else "A", rep)
    else:
        print(__doc__)
        sys.exit(2)
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
