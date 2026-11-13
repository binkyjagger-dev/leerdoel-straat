#!/usr/bin/env python3
"""Checks LB1–LB6 on pattern and knob labels (specs/26 §7), run after label_merge.py.

Usage: check_labels.py <run_dir> [--toets] [--bank <dir>] [--subjects <dir>]

LB1 every question of every opgave has a label from A and from B (files valid against item_labels)
LB2 pattern exists in base + subject catalogue (or is NIEUW with a proposal); a retired pattern warns
LB3 applicability: route only on calculation/schema patterns, schema only on schema patterns, builds_on null on
    the first question of an opgave; a value against a pattern's knobs_fixed warns
LB4 evidence quotes verbatim (question, opgave context, sources or correctievoorschrift) and ≤ 25 words
LB5 builds_on_questions refer to earlier questions of the same opgave; builds_on = ja ⇔ at least one
LB6 points from units; a labeller's points that differ are ignored (warning); merged points = unit points
Writes <run_dir>/26_label_check.json (toets: 34_label_check.json).
"""
from __future__ import annotations

import sys
from pathlib import Path

from lcommon import PREFIX, Run, bank_dir, subjects_dir, load_labeller
from ecommon import MAX_QUOTE_WORDS, Report, load_json, words
from tcommon import kinds_of, knob_applies, pattern_codes


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    mode = "toets" if "--toets" in argv else "exam"
    rep = Report("check_labels")
    subject = load_json(run_dir / "run.json")["subject"]
    run = Run(run_dir, mode, bank_dir(subject, argv), subjects_dir(argv))
    files = {}
    for letter in ("A", "B", "R"):
        items, errs = load_labeller(run, letter)
        for e in errs:
            rep.fail("LB1", e)
        files[letter] = items
    # LB1
    for oid in run.opgaven:
        for letter in ("A", "B"):
            miss = [q["question_number"] for q in run.questions_of(oid) if q["question_id"] not in files[letter]]
            if miss:
                rep.fail("LB1", f"{oid}: labeller {letter} has no label for question(s) {miss}")
    for letter, items in files.items():
        for qid, it in items.items():
            q = run.questions.get(qid)
            tag = f"{it['_file']} {qid}"
            if not q:
                rep.fail("LB1", f"{tag}: not a question of this run")
                continue
            if it["_opgave"] != q["opgave_id"]:
                rep.fail("LB1", f"{tag}: in the file of {it['_opgave']} but belongs to {q['opgave_id']}")
            check_item(rep, run, q, it, tag, repair=letter == "R")
    # merged file
    mp = run_dir / f"{PREFIX[mode]}.json"
    if mp.exists():
        for l in load_json(mp)["labels"]:
            q = run.questions.get(l["question_id"])
            if q and l["points"] != q["points"]:
                rep.fail("LB6", f"merged {l['question_id']}: points {l['points']} != unit points {q['points']}")
            for code in pattern_codes(l["pattern"]):
                if code != "NIEUW" and code not in run.pidx:
                    rep.fail("LB2", f"merged {l['question_id']}: pattern {code} not in the catalogue")
    else:
        rep.warn("LB1", f"{mp.name} not found: run label_merge.py first for the merged checks")
    n = sum(len(v) for v in files.values())
    rep.info("LB1", f"{len(run.questions)} questions, {n} labeller items checked (A {len(files['A'])}, "
                    f"B {len(files['B'])}, R {len(files['R'])})")
    rep.print_and_exit(str(run_dir / f"{PREFIX[mode].replace('labels', 'label_check')}.json"))


def check_item(rep: Report, run: Run, q: dict, it: dict, tag: str, repair: bool) -> None:
    pat = it.get("pattern")
    # LB2
    if pat is not None:
        if pat == "NIEUW":
            if not it.get("proposed_pattern"):
                rep.fail("LB2", f"{tag}: NIEUW without proposed_pattern")
        else:
            for code in pattern_codes(pat):
                p = run.pidx.get(code)
                if not p:
                    rep.fail("LB2", f"{tag}: pattern {code} not in base + {run.subject} catalogue")
                elif p.get("status") == "retired":
                    rep.warn("LB2", f"{tag}: pattern {code} is retired ({p.get('retired_by')})")
    # LB3 (only when the item carries a pattern the knob depends on)
    known = pat is not None and pat != "NIEUW" and all(c in run.pidx for c in pattern_codes(pat))
    kinds = kinds_of(pat, run.pidx) if known else set()
    for k in ("route", "schema"):
        if k not in it or not known:
            continue
        applies = knob_applies(run.knobs[k], kinds, q["first_of_opgave"])
        if not applies and it[k] is not None:
            rep.fail("LB3", f"{tag}: {k}='{it[k]}' on pattern {pat} ({'/'.join(sorted(kinds))}); must be null")
        if applies and it[k] is None and not repair:
            rep.fail("LB3", f"{tag}: {k} is null but applies to pattern {pat}")
    if "builds_on" in it:
        if q["first_of_opgave"] and it["builds_on"] is not None:
            rep.fail("LB3", f"{tag}: builds_on on the first question of the opgave; must be null")
        if not q["first_of_opgave"] and it["builds_on"] is None:
            rep.fail("LB3", f"{tag}: builds_on is null but the question is not the first of its opgave")
    if known:
        for code in pattern_codes(pat):
            for k, v in run.pidx[code]["knobs_fixed"].items():
                if k in it and it[k] is not None and it[k] != v and len(pattern_codes(pat)) == 1:
                    rep.warn("LB3", f"{tag}: {k}='{it[k]}' but pattern {code} fixes {k}='{v}'")
    # LB4
    for field, quote in (it.get("evidence") or {}).items():
        if words(quote) > MAX_QUOTE_WORDS:
            rep.fail("LB4", f"{tag}: evidence for {field} has {words(quote)} words (max {MAX_QUOTE_WORDS})")
        elif not run.evidence_ok(q["question_id"], quote):
            rep.fail("LB4", f"{tag}: evidence for {field} not verbatim in the question, context, sources or cv: "
                            f"'{quote[:60]}'")
    if not repair:
        for f in ("pattern", "solo", "steps", "sources"):
            if f not in (it.get("evidence") or {}):
                rep.warn("LB4", f"{tag}: no evidence for {f}")
    # LB5
    if "builds_on" in it or "builds_on_questions" in it:
        refs = it.get("builds_on_questions") or []
        earlier = [n for n in q["opgave_numbers"] if n < q["question_number"]]
        bad = [n for n in refs if n not in earlier]
        if bad:
            rep.fail("LB5", f"{tag}: builds_on_questions {bad} are not earlier questions of the same opgave {earlier}")
        if it.get("builds_on") == "ja" and not refs:
            rep.fail("LB5", f"{tag}: builds_on = ja without builds_on_questions")
        if it.get("builds_on") in ("nee", None) and refs and "builds_on" in it:
            rep.fail("LB5", f"{tag}: builds_on_questions given but builds_on = {it.get('builds_on')}")
    # LB6
    if it.get("points") is not None and it["points"] != q["points"]:
        rep.warn("LB6", f"{tag}: labeller points {it['points']} ignored (unit points {q['points']})")


if __name__ == "__main__":
    main(sys.argv)
