#!/usr/bin/env python3
"""Subject glossary: criterion term <- source synonyms, for candidate retrieval (specs/06 §8).

Usage:
  glossary.py add      <subject> <decision_id> <entries.json> [--scope <id>|--no-scope]
        entries.json = [{"term": "couponrente", "synonyms": ["interestvoet", ...]}, ...]
        refuses unless <decision_id> is an *answered* decision of the subject; scope defaults to the
        decision's scope; re-adding a decision replaces its entries
  glossary.py list     <subject>
  glossary.py validate <subject>

Option --subjects <dir> replaces subjects/ (used by the fixture test).
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from common import ROOT, load_json, save_json, validate_schema

sys.path.insert(0, str(ROOT / "scripts" / "mapping"))
from mcommon import norm  # noqa: E402


def _path(subjects: Path, subject: str) -> Path:
    return subjects / subject / "glossary.json"


def check(data: dict) -> list[str]:
    """Schema plus: a synonym (normalised) maps to one term only and is never itself a term in the same scope."""
    errs = validate_schema(data, "glossary.schema.json")
    if errs:
        return errs
    by_scope = defaultdict(dict)
    terms = defaultdict(set)
    for e in data["entries"]:
        terms[e["scope"]].add(norm(e["term"]))
    for e in data["entries"]:
        for s in e["synonyms"]:
            k, t = norm(s), norm(e["term"])
            if k == t:
                errs.append(f"{e['decision']}: synonym '{s}' equals its term")
            prev = by_scope[e["scope"]].get(k)
            if prev and prev != t:
                errs.append(f"{e['decision']}: synonym '{s}' maps to '{e['term']}' and to '{prev}' (scope {e['scope']})")
            by_scope[e["scope"]][k] = t
            if k in terms[e["scope"]] or k in terms[None]:
                errs.append(f"{e['decision']}: synonym '{s}' is also a term — chains are not allowed")
    return errs


def cmd_add(subjects: Path, subject: str, did: str, entries_path: str, scope_opt: str | None, no_scope: bool) -> None:
    dp = subjects / subject / "decisions.json"
    if not dp.exists():
        sys.exit(f"no decisions file for subject '{subject}'")
    dec = next((d for d in load_json(dp)["decisions"] if d["id"] == did), None)
    if not dec:
        sys.exit(f"decision {did} not found in {dp}")
    if dec["status"] != "answered":
        sys.exit(f"decision {did} has status {dec['status']!r}; only an answered decision can add glossary entries")
    new = load_json(entries_path)
    scope = None if no_scope else (scope_opt or dec.get("scope"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = _path(subjects, subject)
    data = load_json(p) if p.exists() else {"subject": subject, "entries": []}
    kept = [e for e in data["entries"] if e["decision"] != did]
    data["entries"] = kept + [{"term": e["term"], "synonyms": e["synonyms"], "scope": scope, "decision": did,
                               "added_at": today} for e in new]
    errs = check(data)
    if errs:
        sys.exit("refusing to write invalid glossary.json:\n  " + "\n  ".join(errs))
    save_json(p, data)
    print(f"[glossary] {subject}: {len(new)} entries from {did} (scope {scope}); {len(data['entries'])} in total")


def cmd_list(subjects: Path, subject: str) -> None:
    p = _path(subjects, subject)
    if not p.exists():
        print(f"[glossary] {subject}: no glossary")
        return
    for e in load_json(p)["entries"]:
        print(f"{e['term']} <- {', '.join(e['synonyms'])}   [{e['scope'] or 'vak'} · {e['decision']}]")


def cmd_validate(subjects: Path, subject: str) -> None:
    p = _path(subjects, subject)
    if not p.exists():
        print(f"[glossary] {subject}: no glossary")
        return
    errs = check(load_json(p))
    if errs:
        sys.exit("[glossary] invalid:\n  " + "\n  ".join(errs))
    print(f"[glossary] {subject}: valid")


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    rest = argv[3:]

    def opt(flag: str) -> str | None:
        return rest[rest.index(flag) + 1] if flag in rest else None

    subjects = Path(opt("--subjects")) if opt("--subjects") else ROOT / "subjects"
    cmd, subject = argv[1], argv[2]
    if cmd == "add" and len(rest) >= 2:
        cmd_add(subjects, subject, rest[0], rest[1], opt("--scope"), "--no-scope" in rest)
    elif cmd == "list":
        cmd_list(subjects, subject)
    elif cmd == "validate":
        cmd_validate(subjects, subject)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
