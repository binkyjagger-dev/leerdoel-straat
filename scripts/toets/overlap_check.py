#!/usr/bin/env python3
"""T3 — no copying from exam text (specs/34 §3, OV).

Usage: overlap_check.py <run_dir> --opgave <id> [--subjects <dir>]

8-word shingles (lower case, accents and punctuation stripped, every number masked as '#') of the opgave's intro,
stems, sources and model answers are compared with the style examples in 33_examples/*.md and with all exam text in
text/*.txt when present. Any shared shingle fails. Phrases on the 'Overlap-allowlist' of the subject's
conventions.md (fixed exam wording such as "voor elke fout 1 scorepunt in mindering brengen") are cut out of the
opgave's text first, so they never form a shingle.
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mapping"))
from mcommon import norm  # noqa: E402
from items_check import texts_of  # noqa: E402
from tcommon import Report, load_json  # noqa: E402
from toetsrun import ToetsRun, opt, subjects_opt  # noqa: E402

N = 8
BREAK = "\x00"


def tokens(text: str) -> list[str]:
    return ["#" if re.search(r"\d", t) else t for t in norm(text).split()]


def shingles(toks: list[str]) -> set[tuple[str, ...]]:
    out, seg = set(), []
    for t in toks + [BREAK]:
        if t == BREAK:
            out |= {tuple(seg[i:i + N]) for i in range(len(seg) - N + 1)}
            seg = []
        else:
            seg.append(t)
    return out


def cut_allowlist(toks: list[str], phrases: list[list[str]]) -> list[str]:
    toks = list(toks)
    for ph in sorted(phrases, key=len, reverse=True):
        n = len(ph)
        i = 0
        while i <= len(toks) - n:
            if toks[i:i + n] == ph:
                toks[i:i + n] = [BREAK]
            i += 1
    return toks


def main(argv: list[str]) -> None:
    if len(argv) < 2 or not opt(argv, "--opgave"):
        print(__doc__)
        sys.exit(2)
    R, oid = Path(argv[1]), opt(argv, "--opgave")
    rep = Report(f"overlap_check {oid}")
    run = ToetsRun(R, subjects_opt(argv))
    it = load_json(R / "33_items" / f"{oid}.json")
    allow = [tokens(p) for p in run.allowlist() if p.strip()]
    parts = [("intro", it["intro"])] + [(f"{v['vraag_id']} stem", v["stem"]) for v in it["vragen"]]
    parts += [(f"informatiebron {s['n']}", t) for s in it["sources"] for t in texts_of([s.get("title"), s.get("text"), s.get("table")])]
    parts += [(f"{v['vraag_id']} model answer", v["cv"]["model_answer"]) for v in it["vragen"]]
    mine = {}
    for where, text in parts:
        for sh in shingles(cut_allowlist(tokens(text), allow)):
            mine.setdefault(sh, where)
    exam_files = sorted(glob.glob(str(R / "33_examples" / "*.md"))) + sorted(glob.glob(str(R / "text" / "*.txt")))
    if not exam_files:
        rep.warn("OV", "no style examples and no exam text in the run: nothing to compare with")
    hits = 0
    for f in exam_files:
        theirs = shingles(tokens(Path(f).read_text(encoding="utf-8")))
        for sh in sorted(set(mine) & theirs):
            hits += 1
            rep.fail("OV", f"{mine[sh]}: shares '{' '.join(sh)}' with {Path(f).parent.name}/{Path(f).name}")
    rep.info("OV", f"{len(mine)} shingles of {oid} compared with {len(exam_files)} exam files; {hits} shared; "
                   f"{len(allow)} allowlist phrases")
    rep.print_and_exit(str(R / "33_checks" / f"{oid}.overlap.json"))


if __name__ == "__main__":
    main(sys.argv)
