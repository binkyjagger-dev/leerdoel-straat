#!/usr/bin/env python3
"""Subject verb tables (specs/02 §2 rule 6, specs/06 §7).

A syllabus may define its own handelingswerkwoorden -> Bloom table. The ingest transcribes it to
<run_dir>/01_verb_table.json; the intake asks whether to adopt it; this script installs the adopted
table as subjects/<subject>/bloom_verbs.json and computes the *effective* table (generic + overlay).

Usage:
  verb_table.py scan      <pdf> [--out <scan.json>]
        deterministic: pages mentioning handelingswerkwoord / beheersingsniveau / taxonomie van Bloom
  verb_table.py validate  <verb_table.json>
        schema + levels + duplicate verbs
  verb_table.py diff      <verb_table.json> [--subject <slug>] [--out <diff.json>]
        compare with the subject's current effective table (generic when it has none):
        conflicts (verb classified differently), new verbs, agreements
  verb_table.py install   <subject> <verb_table.json> --decision <id> [--drop <verb>]... [--force]
        write subjects/<subject>/bloom_verbs.json; refuses unless <id> is an *answered* decision
        of that subject; --drop removes a verb (it keeps its generic level); --force overwrites
  verb_table.py effective <subject> [--out <path>]
        print (or write) the merged table every agent and validator uses
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import (BLOOM_ORDER, SUBJECTS, Report, load_bloom_rules, load_json, save_json, stem_verb,
                    validate_schema)

SIGNALS = [r"handelingswerkwoord", r"beheersingsniveau", r"taxonomie\s+van\s+bloom"]


# ---------------------------------------------------------------- scan ----
def _pages_text(pdf: str) -> list[str]:
    try:
        import pymupdf  # type: ignore
        doc = pymupdf.open(pdf)
        return [p.get_text() for p in doc]
    except ImportError:
        pass
    try:
        import fitz  # type: ignore
        doc = fitz.open(pdf)
        return [p.get_text() for p in doc]
    except ImportError:
        pass
    out = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    if out.returncode != 0:
        sys.exit("verb_table.py scan: need PyMuPDF (pip install pymupdf) or pdftotext")
    return out.stdout.split("\f")


def cmd_scan(pdf: str, out: str | None) -> None:
    pages = _pages_text(pdf)
    hits = []
    for i, t in enumerate(pages, 1):
        counts = {s: len(re.findall(s, t, re.I)) for s in SIGNALS}
        n = sum(counts.values())
        if n:
            levels = sum(1 for lvl in ("memoriseren", "onthouden", "begrijpen", "toepassen", "analyseren",
                                       "evalueren", "creëren") if re.search(lvl, t, re.I))
            hits.append({"page": i, "signals": n, "bloom_levels_named": levels,
                         "likely_table": levels >= 5})
    result = {"pdf": pdf, "pages_total": len(pages), "found": bool(hits), "pages": hits,
              "likely_table_pages": [h["page"] for h in hits if h["likely_table"]]}
    if out:
        save_json(out, result)
    print(f"[verb_table] scan: {len(hits)} page(s) with verb-taxonomy signals"
          + (f"; likely table on page(s) {result['likely_table_pages']}" if result["likely_table_pages"] else ""))
    for h in hits:
        print(f"  p{h['page']}: {h['signals']} signal(s), {h['bloom_levels_named']} Bloom level names"
              + ("  <- likely table" if h["likely_table"] else ""))
    if not hits:
        print("  no own handelingswerkwoorden table detected; the generic verb table applies")


# ------------------------------------------------------------ validate ----
def _check_table(tab: dict, rep: Report) -> None:
    for e in validate_schema(tab, "verb_table.schema.json"):
        rep.fail("V1", e)
    seen: dict[str, list[str]] = {}
    for lvl, verbs in (tab.get("verbs") or {}).items():
        if lvl not in BLOOM_ORDER:
            rep.fail("V2", f"unknown level {lvl!r}")
        for v in verbs:
            if v != v.lower():
                rep.warn("V3", f"{lvl}: verb {v!r} is not lower-case")
            seen.setdefault(stem_verb(v), []).append(lvl)
    for v, lvls in seen.items():
        if len(set(lvls)) > 1 and v not in {stem_verb(k) for k in (tab.get("ambiguous") or {})}:
            rep.warn("V4", f"verb {v!r} listed at {sorted(set(lvls))}; it becomes ambiguous between those levels")
    if not any((tab.get("verbs") or {}).values()):
        rep.fail("V5", "table has no verbs")


def cmd_validate(path: str) -> None:
    rep = Report("verb_table")
    _check_table(load_json(path), rep)
    rep.print_and_exit()


# ---------------------------------------------------------------- diff ----
def _classify(eff: dict, verb: str) -> list[str]:
    s = stem_verb(verb)
    amb = next((v for k, v in eff.get("ambiguous", {}).items() if stem_verb(k) == s), None)
    if amb:
        return list(amb)
    return [lvl for lvl, vs in eff["verbs"].items() if any(stem_verb(x) == s for x in vs)]


def compute_diff(tab: dict, subject: str | None) -> dict:
    eff = load_bloom_rules(subject)
    conflicts, new, same = [], [], []
    for lvl, verbs in (tab.get("verbs") or {}).items():
        for v in verbs:
            cur = _classify(eff, v)
            hint = eff.get("source_verb_hints", {}).get(stem_verb(v))
            if not cur:
                new.append({"verb": stem_verb(v), "source_level": lvl})
            elif cur == [lvl]:
                same.append(stem_verb(v))
            else:
                conflicts.append({"verb": stem_verb(v), "source_level": lvl, "current_levels": cur,
                                  "current_hint": hint,
                                  "kind": "narrowed" if lvl in cur else "reclassified"})
    return {"subject": subject, "compared_with": eff["_effective"]["overlay"] or eff["_effective"]["generic"],
            "conflicts": conflicts, "new": new, "same": same}


def cmd_diff(path: str, subject: str | None, out: str | None) -> None:
    d = compute_diff(load_json(path), subject)
    if out:
        save_json(out, d)
    n_re = sum(1 for c in d["conflicts"] if c["kind"] == "reclassified")
    print(f"[verb_table] diff against {d['compared_with']}: {len(d['conflicts'])} conflict(s) "
          f"({n_re} reclassified, {len(d['conflicts']) - n_re} narrowed from ambiguous), "
          f"{len(d['new'])} new verb(s), {len(d['same'])} agree")
    for c in d["conflicts"]:
        tag = "RECLASS " if c["kind"] == "reclassified" else "NARROWED"
        print(f"  {tag} {c['verb']!r}: source {c['source_level']} | current {'/'.join(c['current_levels'])}")
    for n in d["new"]:
        print(f"  NEW      {n['verb']!r}: {n['source_level']}")


# ------------------------------------------------------------- install ----
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_install(subject: str, path: str, decision: str | None, drops: list[str], force: bool) -> None:
    tab = load_json(path)
    rep = Report("verb_table")
    _check_table(tab, rep)
    if rep.failed:
        rep.print_and_exit()
    if not decision:
        sys.exit("verb_table.py install: --decision <id> is required (the answered decision that adopts the table)")
    dpath = SUBJECTS / subject / "decisions.json"
    if not dpath.exists():
        sys.exit(f"no decisions file for subject {subject!r}; run decisions.py init {subject} first")
    dec = next((d for d in load_json(dpath)["decisions"] if d["id"] == decision), None)
    if dec is None:
        sys.exit(f"decision {decision} not found in {dpath}")
    if dec["status"] != "answered":
        sys.exit(f"decision {decision} has status {dec['status']!r}; only an answered decision can install a verb table")
    target = SUBJECTS / subject / "bloom_verbs.json"
    if target.exists() and not force:
        sys.exit(f"{target} exists; use --force to replace it (the old table is kept as bloom_verbs.previous.json)")
    dropped = []
    for lvl in list(tab["verbs"]):
        keep = []
        for v in tab["verbs"][lvl]:
            if stem_verb(v) in {stem_verb(x) for x in drops}:
                dropped.append(v)
            else:
                keep.append(v)
        tab["verbs"][lvl] = keep
    tab["subject"] = subject
    tab["decision"] = decision
    tab["installed_at"] = _now()
    if dropped:
        tab["notes"] = ((tab.get("notes") or "") + f" Dropped at install (keep generic level): {', '.join(dropped)}.").strip()
    if target.exists():
        target.replace(target.with_name("bloom_verbs.previous.json"))
    save_json(target, tab)
    n = sum(len(v) for v in tab["verbs"].values())
    print(f"[verb_table] installed {n} verbs for {subject} -> {target} (decision {decision}"
          + (f", dropped {dropped}" if dropped else "") + ")")


# ----------------------------------------------------------- effective ----
def cmd_effective(subject: str, out: str | None) -> None:
    eff = load_bloom_rules(subject)
    meta = eff["_effective"]
    if out:
        save_json(out, eff)
    changed = [o for o in meta["overrides"] if o["changed"]]
    if meta["overlay"]:
        print(f"[verb_table] effective table for {subject}: generic + {meta['overlay']} "
              f"({len(meta['overrides'])} verbs from the subject table, {len(changed)} reclassified; decision {meta['decision']})")
        for o in changed:
            was = "/".join(o["generic_levels"]) if o["generic_levels"] else ("hint:" + o["generic_hint"] if o["generic_hint"] else "not listed")
            print(f"  {o['verb']!r}: {o['level']}  (generic: {was}{', ambiguous' if o['generic_ambiguous'] else ''})")
    else:
        print(f"[verb_table] effective table for {subject}: generic only (no subjects/{subject}/bloom_verbs.json)")
    if out:
        print(f"  -> {out}")


# ---------------------------------------------------------------- main ----
def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    cmd, rest = argv[1], argv[2:]

    def opt(flag: str) -> str | None:
        return rest[rest.index(flag) + 1] if flag in rest else None

    def opts(flag: str) -> list[str]:
        return [rest[i + 1] for i, a in enumerate(rest) if a == flag and i + 1 < len(rest)]

    pos = [a for i, a in enumerate(rest) if not a.startswith("--") and (i == 0 or not rest[i - 1].startswith("--")
                                                                        or rest[i - 1] == "--force")]
    if cmd == "scan":
        cmd_scan(pos[0], opt("--out"))
    elif cmd == "validate":
        cmd_validate(pos[0])
    elif cmd == "diff":
        cmd_diff(pos[0], opt("--subject"), opt("--out"))
    elif cmd == "install":
        cmd_install(pos[0], pos[1], opt("--decision"), opts("--drop"), "--force" in rest)
    elif cmd == "effective":
        cmd_effective(pos[0], opt("--out"))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
