#!/usr/bin/env python3
"""Manage subjects/<subject>/decisions.json (specs/06-subject-profiles.md).

Usage:
  decisions.py init     <subject>                       create subjects/<subject>/ with empty decisions + profile template
  decisions.py validate <subject>
  decisions.py list     <subject> [--open]              print decisions (open only with --open)
  decisions.py add      <subject> <intake_questions.json> --run <run_id>
                                                         append questions as open decisions (skips duplicate keys/questions)
  decisions.py answer   <subject> <id> "<answer>" [--by <name>] [--run <run_id>]
  decisions.py answer-file <subject> <answers.json> [--by <name>] [--run <run_id>]
                                                         answers.json = {"<id>": "<answer>", ...}
  decisions.py snapshot <subject> <run_dir>              write answered+open decisions into <run_dir>/decisions_snapshot.json
  decisions.py render   <subject> [--open]               markdown table (for the pause prompt / reports)

Decisions are append-only; answering an already-answered decision supersedes it with a new id.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import ROOT, load_json, save_json, validate_schema

SUBJECTS = ROOT / "subjects"

PROFILE_TEMPLATE = """# Vakprofiel — {subject}

Door de docent geschreven context. De straat leest dit bestand in elke rol en schrijft er nooit in.
Antwoorden op intakevragen komen in `decisions.json`.

## Scope
- Niveaus / examenprogramma:
- Wat buiten scope valt:

## Methode
- Methode en editie:
- Conventies uit de methode die leidend zijn:

## Terminologie
- Voorkeurstermen (en wat we niet gebruiken):

## Afspraken
- Interpretaties waar de sectie afspraken over heeft gemaakt:

## Niet doen
-
"""


def _path(subject: str) -> Path:
    return SUBJECTS / subject / "decisions.json"


def _load(subject: str) -> dict:
    p = _path(subject)
    if not p.exists():
        sys.exit(f"no decisions file for subject '{subject}' — run: decisions.py init {subject}")
    return load_json(p)


def _save(subject: str, data: dict) -> None:
    errs = validate_schema(data, "decisions.schema.json")
    if errs:
        sys.exit("refusing to write invalid decisions.json:\n  " + "\n  ".join(errs))
    save_json(_path(subject), data)


def _next_id(subject: str, data: dict) -> str:
    prefix = re.sub(r"[^a-z0-9-]", "", subject.lower())[:12] or "subj"
    nums = [int(d["id"].rsplit("-", 1)[1]) for d in data["decisions"] if d["id"].startswith(prefix + "-")]
    return f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(q: str) -> str:
    return re.sub(r"\W+", " ", q.lower()).strip()


def cmd_init(subject: str) -> None:
    d = SUBJECTS / subject
    d.mkdir(parents=True, exist_ok=True)
    if not _path(subject).exists():
        _save(subject, {"subject": subject, "decisions": []})
    prof = d / "profile.md"
    if not prof.exists():
        prof.write_text(PROFILE_TEMPLATE.format(subject=subject), encoding="utf-8")
    print(f"[decisions] subject '{subject}' ready at {d}")


def cmd_validate(subject: str) -> None:
    errs = validate_schema(_load(subject), "decisions.schema.json")
    for e in errs:
        print("  FAIL", e)
    print(f"[decisions] {subject}: {'valid' if not errs else str(len(errs)) + ' errors'}")
    sys.exit(1 if errs else 0)


def cmd_list(subject: str, open_only: bool) -> None:
    for d in _load(subject)["decisions"]:
        if open_only and d["status"] != "open":
            continue
        ans = d.get("answer") or f"(voorgesteld: {d['proposed']})"
        print(f"{d['id']} [{d['status']}/{d['impact']}] {d['question']}\n    -> {ans}")


def cmd_add(subject: str, questions_path: str, run_id: str | None) -> None:
    data = _load(subject)
    iq = load_json(questions_path)
    existing = {_norm(d["question"]) for d in data["decisions"] if d["status"] != "superseded"}
    added = 0
    for q in iq["questions"]:
        if _norm(q["question"]) in existing:
            continue
        data["decisions"].append({
            "id": _next_id(subject, data), "question": q["question"], "context": q.get("context"),
            "options": q.get("options"), "proposed": q["proposed"], "impact": q["impact"],
            "applies_to": q["applies_to"], "affects_units": q.get("affects_units"),
            "status": "open", "answer": None, "answered_by": None, "answered_at": None,
            "source_run": run_id, "raised_by": iq.get("raised_by", "intake"), "supersedes": None,
        })
        existing.add(_norm(q["question"]))
        added += 1
    _save(subject, data)
    print(f"[decisions] added {added} open decision(s) to {subject}")


def _answer_one(data: dict, subject: str, did: str, answer: str, by: str | None, run_id: str | None) -> str:
    cur = next((d for d in data["decisions"] if d["id"] == did), None)
    if cur is None:
        sys.exit(f"unknown decision id {did}")
    if cur["status"] == "answered":
        new = dict(cur)
        new.update(id=_next_id(subject, data), supersedes=cur["id"], status="answered", answer=answer,
                   answered_by=by, answered_at=_now(), source_run=run_id or cur.get("source_run"))
        cur["status"] = "superseded"
        data["decisions"].append(new)
        return new["id"]
    cur.update(status="answered", answer=answer, answered_by=by, answered_at=_now(),
               source_run=run_id or cur.get("source_run"))
    return cur["id"]


def cmd_answer(subject: str, did: str, answer: str, by: str | None, run_id: str | None) -> None:
    data = _load(subject)
    nid = _answer_one(data, subject, did, answer, by, run_id)
    _save(subject, data)
    print(f"[decisions] {nid} answered")


def cmd_answer_file(subject: str, answers_path: str, by: str | None, run_id: str | None) -> None:
    data = _load(subject)
    answers = load_json(answers_path)
    for did, ans in answers.items():
        _answer_one(data, subject, did, ans, by, run_id)
    _save(subject, data)
    print(f"[decisions] {len(answers)} decision(s) answered")


def cmd_snapshot(subject: str, run_dir: str) -> None:
    data = _load(subject)
    snap = {"subject": subject, "taken_at": _now(),
            "decisions": [{"id": d["id"], "status": d["status"], "question": d["question"],
                           "effective_answer": d["answer"] if d["status"] == "answered" else d["proposed"],
                           "provisional": d["status"] != "answered", "applies_to": d["applies_to"],
                           "affects_units": d.get("affects_units")}
                          for d in data["decisions"] if d["status"] != "superseded"]}
    save_json(Path(run_dir) / "decisions_snapshot.json", snap)
    n_open = sum(1 for d in snap["decisions"] if d["provisional"])
    print(f"[decisions] snapshot: {len(snap['decisions'])} decisions ({n_open} provisional) -> {run_dir}/decisions_snapshot.json")


def cmd_render(subject: str, open_only: bool) -> None:
    rows = [d for d in _load(subject)["decisions"] if d["status"] != "superseded" and (not open_only or d["status"] == "open")]
    print("| id | status | impact | vraag | antwoord / voorstel |\n|---|---|---|---|---|")
    for d in rows:
        ans = d["answer"] if d["status"] == "answered" else f"*voorstel:* {d['proposed']}"
        print(f"| {d['id']} | {d['status']} | {d['impact']} | {d['question']} | {ans} |")


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    cmd, subject, rest = argv[1], argv[2], argv[3:]
    slug = re.sub(r"[^a-z0-9-]+", "-", subject.strip().lower()).strip("-")
    if slug != subject:
        print(f"[decisions] subject name normalised: '{subject}' -> '{slug}' (use this with --subject)")
        subject = slug

    def opt(flag: str) -> str | None:
        return rest[rest.index(flag) + 1] if flag in rest else None

    if cmd == "init":
        cmd_init(subject)
    elif cmd == "validate":
        cmd_validate(subject)
    elif cmd == "list":
        cmd_list(subject, "--open" in rest)
    elif cmd == "add":
        cmd_add(subject, rest[0], opt("--run"))
    elif cmd == "answer":
        cmd_answer(subject, rest[0], rest[1], opt("--by"), opt("--run"))
    elif cmd == "answer-file":
        cmd_answer_file(subject, rest[0], opt("--by"), opt("--run"))
    elif cmd == "snapshot":
        cmd_snapshot(subject, rest[0])
    elif cmd == "render":
        cmd_render(subject, "--open" in rest)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
