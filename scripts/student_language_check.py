#!/usr/bin/env python3
"""Student-language rules L1–L4 (specs/02 §4, specs/04 §2).

Usage: student_language_check.py <04_groups_student.json> [<03_groups_raw.json>]

  L1  every text_student starts with the required opener ("Ik kan ")
  L2  no forbidden openers / phrases
  L3  single sentence, <= max words (warning)
  L4  ids, bloom, bloom_verb, criterion counts unchanged versus the raw file (if given)
"""
from __future__ import annotations

import re
import sys

from common import DATA, Report, load_json


def _sentences(s: str) -> int:
    return len([p for p in re.split(r"[.!?]+", s.strip()) if p.strip()])


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    rules = load_json(DATA / "student_language_rules.json")
    opener = rules["required_opener"]
    bad_openers = [o.lower() for o in rules["forbidden_openers"]]
    bad_phrases = [p.lower() for p in rules["forbidden_phrases"]]
    max_words = rules["max_words_per_sentence"]
    max_sent = rules["max_sentences"]

    rep = Report("student_language_check")
    data = load_json(argv[1])
    raw = load_json(argv[2]) if len(argv) > 2 else None

    def check_text(ident: str, text: str | None) -> None:
        if not text:
            rep.fail("L1", f"{ident}: text_student missing")
            return
        if not text.startswith(opener):
            rep.fail("L1", f"{ident}: does not start with '{opener.strip()}': {text[:40]!r}")
        low = text.lower()
        for o in bad_openers:
            if low.startswith(o.lower()):
                rep.fail("L2", f"{ident}: forbidden opener '{o}'")
        for p in bad_phrases:
            if re.search(rf"\b{re.escape(p)}\b", low):
                rep.fail("L2", f"{ident}: forbidden phrase '{p}'")
        words = len(text.split())
        if words > max_words:
            rep.warn("L3", f"{ident}: {words} words (> {max_words})")
        if _sentences(text) > max_sent:
            rep.warn("L3", f"{ident}: more than {max_sent} sentence(s)")

    for g in data["groups"]:
        check_text(g["group_id"], g["goal"].get("text_student"))
        for c in g["criteria"]:
            check_text(c["criterion_id"], c.get("text_student"))

    if raw:
        raw_by_id = {g["group_id"]: g for g in raw["groups"]}
        for g in data["groups"]:
            r = raw_by_id.get(g["group_id"])
            if r is None:
                rep.fail("L4", f"{g['group_id']}: not present in raw file")
                continue
            if g["unit_id"] != r["unit_id"] or g["source_quote"] != r["source_quote"]:
                rep.fail("L4", f"{g['group_id']}: unit_id/source_quote changed")
            if g["goal"]["text_expert"] != r["goal"]["text_expert"]:
                rep.fail("L4", f"{g['group_id']}: goal.text_expert changed")
            if len(g["criteria"]) != len(r["criteria"]):
                rep.fail("L4", f"{g['group_id']}: criterion count changed")
                continue
            for c, rc in zip(g["criteria"], r["criteria"]):
                for k in ("criterion_id", "text_expert", "bloom", "bloom_verb"):
                    if c[k] != rc[k]:
                        rep.fail("L4", f"{c['criterion_id']}: {k} changed")
        for gid in set(raw_by_id) - {g["group_id"] for g in data["groups"]}:
            rep.fail("L4", f"{gid}: dropped by student-language step")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
