#!/usr/bin/env python3
"""Deterministic text metrics of the bank's exams — the central-exam house rules (specs/36 §3.1, §11 B3, B9, B10).

Usage: exam_metrics.py <subject> [--exam <exam_id> ...] [--bank <dir>] [--subjects <dir>]
                       [--duration <exam_id>=<minutes> ...] [--decision <decision-id>]

Per exam of B/register.json (or the --exam ids) it re-extracts the text from the PDF paths in the register with
exam_text.py into a temporary folder (deleted afterwards; never committed) and writes **counts only** to
B/metrics/<exam_id>.json (schema exam_metrics):
  exam:    duration_minutes (cover page "13.30 - 16.30 uur" / "tijdsduur …"), max_score, n_opgaven, n_vragen, n_groups
  opgave:  points, n_vragen, n_groups (distinct group_ids of its linked scorepunten in B/links/), words_intro (all text
           before the first vraag, §11 B10), words_sources (its numbered informatiebronnen)
  vraag:   points, words_lead (the text between the previous vraag and this one; empty for the first vraag),
           words_task (the line(s) after "Np n"), n_tasks (scripts/toets/tasks.py), numbers_lead (numbers in the lead
           that are not in the intro or the sources), pattern (from B/labels/<exam_id>.json when present)
Duration not on the cover → duration_minutes null and an intake-format question (proposal 180 minutes) in
B/metrics/_proposed_decisions.json for `decisions.py add` (the orchestrator). After the answer:
--duration <exam_id>=180 --decision <id> records the value with duration_source "decision <id>" (without
--decision: "manual"). Afterwards run profile_build.py <subject> (house_rules).
EM1 exam PDFs missing at the register paths (that exam is skipped) · EM2 schema · EM3 duration not found (warning) ·
EM4 the parse does not reproduce the register's number of vragen and points (that exam is not written)
"""
from __future__ import annotations

import re
import sys
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "toets"))
from ecommon import ROOT, Report, load_json, save_json, validate_schema  # noqa: E402
import exam_text  # noqa: E402
from tasks import count_tasks, load_rules, new_numbers, words  # noqa: E402

TIME_RANGE = re.compile(r"\b(\d{1,2})[.:](\d{2})\s*(?:-|–|—|tot)\s*(\d{1,2})[.:](\d{2})(?:\s*uur)?\b", re.I)
TIJDSDUUR = re.compile(r"tijdsduur[:\s]*(\d+(?:,\d+)?)\s*(uur|minuten|min)\b", re.I)
DEFAULT_PROPOSAL = 180


def opt(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None


def opts(argv: list[str], flag: str) -> list[str]:
    return [argv[i + 1] for i, a in enumerate(argv) if a == flag and i + 1 < len(argv)]


def parse_duration(text: str) -> int | None:
    """Minutes from the cover page: '13.30 - 16.30 uur' → 180; 'tijdsduur: 3 uur' → 180."""
    m = TIME_RANGE.search(text)
    if m:
        a = int(m.group(1)) * 60 + int(m.group(2))
        b = int(m.group(3)) * 60 + int(m.group(4))
        if b > a:
            return b - a
    m = TIJDSDUUR.search(text)
    if m:
        v = float(m.group(1).replace(",", "."))
        return int(round(v * 60)) if m.group(2).lower() == "uur" else int(round(v))
    return None


def cover_text(pdf: Path) -> str:
    import pymupdf
    doc = pymupdf.open(pdf)
    return " ".join(doc[i].get_text() for i in range(min(2, len(doc))))


def split_question(text: str, points: int, number: int) -> tuple[str, str]:
    """(context, task) from a question text file: '[context]' lines, then '[vraag]' and 'Np n <task>'."""
    ctx, task, mode = [], [], None
    for ln in text.splitlines():
        s = ln.strip()
        if s == "[context]":
            mode = "c"
            continue
        if s == "[vraag]":
            mode = "v"
            continue
        if mode == "c":
            ctx.append(ln)
        elif mode == "v":
            task.append(ln)
    t = " ".join(x.strip() for x in task if x.strip())
    t = re.sub(rf"^{points}p\s+{number}\s+", "", t)
    return "\n".join(ctx).strip(), t


def resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else ROOT / q


def measure(subject: str, e: dict, bank: Path, rules: dict, tmp: Path, rep: Report) -> dict | None:
    eid = e["exam_id"]
    o = resolve((e.get("files") or {}).get("o", ""))
    if not (e.get("files") or {}).get("o") or not o.exists():
        rep.fail("EM1", f"{eid}: opgaven PDF not found at the register path {(e.get('files') or {}).get('o')!r}; skipped")
        return None
    run_dir = tmp / eid
    (run_dir / "text").mkdir(parents=True)
    meta, units, issues = exam_text.ingest_exam(run_dir, o.parent, subject)
    if meta["exam_id"] != eid:
        rep.fail("EM1", f"{eid}: the PDFs in {o.parent} are exam {meta['exam_id']}; skipped")
        return None
    for x in issues:
        rep.warn("EM1", f"{eid}: exam_text: {x['issue']}")

    def text(ref):
        return (run_dir / ref).read_text(encoding="utf-8") if ref and (run_dir / ref).exists() else ""

    links = defaultdict(set)
    lp = bank / "links" / f"{eid}.json"
    exam_groups = set()
    for sp in (load_json(lp)["scorepunten"] if lp.exists() else []):
        if sp.get("group_id"):
            links[sp["opgave_id"]].add(sp["group_id"])
            exam_groups.add(sp["group_id"])
    labp = bank / "labels" / f"{eid}.json"
    patterns = {q["question_id"]: q.get("pattern") for q in load_json(labp)["questions"]} if labp.exists() else {}
    opgaven, vragen = [], []
    for og in [u for u in units if u["kind"] == "opgave"]:
        qs = sorted((u for u in units if u["kind"] == "question" and u["opgave_id"] == og["unit_id"]), key=lambda q: q["number"])
        bronnen = [text(f"text/{eid}-bron{n}.txt") for n in og.get("sources", [])]
        intro = ""
        parts = []
        for i, q in enumerate(qs):
            ctx, task = split_question(text(q["text_ref"]), q["points"], q["number"])
            if i == 0:
                intro, lead = ctx, ""
            else:
                lead = ctx
            parts.append((q, lead, task))
        for q, lead, task in parts:
            vragen.append({"question_id": q["unit_id"], "number": q["number"], "opgave_id": og["unit_id"], "points": q["points"],
                           "words_lead": words(lead), "words_task": words(task), "n_tasks": count_tasks(task, rules),
                           "numbers_lead": len(new_numbers(lead, [intro] + bronnen)), "pattern": patterns.get(q["unit_id"])})
        opgaven.append({"opgave_id": og["unit_id"], "number": og["number"], "points": sum(q["points"] for q in qs),
                        "n_vragen": len(qs), "n_groups": len(links.get(og["unit_id"], set())), "words_intro": words(intro),
                        "words_sources": sum(words(b) for b in bronnen), "sources": list(og.get("sources", []))})
    nq, pts = len(vragen), sum(v["points"] for v in vragen)
    if nq != (e.get("n_questions") or nq) or pts != (e.get("max_score") or pts):
        rep.fail("EM4", f"{eid}: exam_text parsed {nq} vragen / {pts} p, the register has {e.get('n_questions')} / "
                        f"{e.get('max_score')}: metrics not written (fix the PDF or the parse first)")
        return None
    dur = parse_duration(cover_text(o))
    return {"exam_id": eid, "subject": subject, "built_at": date.today().isoformat(),
            "duration_minutes": dur, "duration_source": "cover" if dur else None,
            "max_score": meta.get("max_score") or e.get("max_score"), "n_opgaven": len(opgaven), "n_vragen": len(vragen),
            "n_groups": len(exam_groups), "opgaven": opgaven, "vragen": vragen}


def duration_question(subject: str, missing: list[str]) -> dict:
    return {"subject": subject, "questions": [{
        "key": "examenduur-" + "-".join(missing)[:60].lower(),
        "question": f"Wat is de tijdsduur van {'het examen' if len(missing) == 1 else 'de examens'} {', '.join(missing)} "
                    f"(nodig voor de huisregel minuten per punt)?",
        "context": "exam_metrics.py vond geen tijdsduur op het voorblad ('13.30 - 16.30 uur' of 'tijdsduur …'). "
                   "Het CvTE-examen VWO duurt 180 minuten. Na het antwoord: exam_metrics.py <vak> --duration "
                   "<examen>=<minuten> --decision <id>, daarna profile_build.py <vak> (specs/36 §3.1, §11 B3).",
        "options": [f"{DEFAULT_PROPOSAL} minuten (CvTE VWO)", "Een andere tijdsduur (typ het aantal minuten)",
                    "Onbekend laten (geen minuten per punt voor dit examen)"],
        "proposed": f"{DEFAULT_PROPOSAL} minuten (CvTE VWO)", "impact": "low", "applies_to": ["planner", "exporter"],
        "affects_units": missing}]}


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[1].startswith("--"):
        print(__doc__)
        sys.exit(2)
    subject = argv[1]
    rep = Report("exam_metrics")
    subjects = Path(opt(argv, "--subjects")) if opt(argv, "--subjects") else ROOT / "subjects"
    bank = Path(opt(argv, "--bank")) if opt(argv, "--bank") else subjects / subject / "examenbank"
    reg = load_json(bank / "register.json")
    want = set(opts(argv, "--exam"))
    overrides = {}
    for d in opts(argv, "--duration"):
        k, _, v = d.partition("=")
        if not v.isdigit():
            sys.exit(f"[exam_metrics] --duration needs <exam_id>=<minutes>, got {d!r}")
        overrides[k] = int(v)
    decision = opt(argv, "--decision")
    rules = load_rules(subject, subjects)
    out = bank / "metrics"
    missing = []
    with tempfile.TemporaryDirectory() as td:
        for e in reg["exams"]:
            if want and e["exam_id"] not in want:
                continue
            m = measure(subject, e, bank, rules, Path(td), rep)
            if m is None:
                continue
            if e["exam_id"] in overrides:
                m["duration_minutes"] = overrides[e["exam_id"]]
                m["duration_source"] = f"decision {decision}" if decision else "manual"
            elif m["duration_minutes"] is None:
                old = out / f"{e['exam_id']}.json"
                prev = load_json(old) if old.exists() else {}
                if prev.get("duration_minutes") and (prev.get("duration_source") or "").startswith(("decision", "manual")):
                    m["duration_minutes"], m["duration_source"] = prev["duration_minutes"], prev["duration_source"]
                else:
                    missing.append(e["exam_id"])
                    rep.warn("EM3", f"{e['exam_id']}: no duration on the cover page: duration_minutes null; question in "
                                    f"metrics/_proposed_decisions.json (proposal {DEFAULT_PROPOSAL} min)")
            for err in validate_schema(m, "exam_metrics.schema.json")[:5]:
                rep.fail("EM2", f"{e['exam_id']}: {err}")
            if rep.failed:
                continue
            save_json(out / f"{e['exam_id']}.json", m)
            words_total = sum(o["words_intro"] + o["words_sources"] for o in m["opgaven"]) + \
                sum(v["words_lead"] + v["words_task"] for v in m["vragen"])
            rep.info("EM2", f"{e['exam_id']}: {m['n_opgaven']} opgaven, {m['n_vragen']} vragen, {m['max_score']} p, "
                            f"{words_total} woorden, duur {m['duration_minutes']} min ({m['duration_source']}) -> "
                            f"metrics/{e['exam_id']}.json")
    pq = out / "_proposed_decisions.json"
    if missing:
        save_json(pq, duration_question(subject, missing))
    elif pq.exists() and not want:
        pq.unlink()
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
