#!/usr/bin/env python3
"""T3 — style examples per pattern for the toets-writer (specs/33 §3 T3).

Usage: exam_examples.py <run_dir> [--bank <dir>] [--subjects <dir>]

For every pattern in 32_blueprint.json writes 33_examples/<pattern>.md: the catalogue description, stem forms and
scoring, then per `example_ref` of the blueprint ("<exam_id> v<n>", optionally prefixed by the subject) the
question text, the informatiebronnen it names and its correctievoorschrift entry, from R/text/
(<exam>-q<n>.txt, <exam>-q<n>.cv.txt, <exam>-bron<n>.txt). When an exam's text is not in R/text/ yet, the exam PDFs
at the paths in the bank register are parsed with scripts/exam/exam_text.py (into R/_exam/, text copied to R/text/).
A missing PDF leaves the pattern with its catalogue description only; the refs are listed in run.json
`examples_missing`. Exam text stays in the run folder (git-ignored); the files say: form only.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from nlnum import REF_RE
from tcommon import ROOT, load_json, pattern_codes, save_json
from toetsrun import ToetsRun, opt, subjects_opt

REF = re.compile(r"((?:vwo|havo|vmbo)-\d{4}-tv\d(?:-[a-z0-9]+)?)\s+v(\d+)")


def ensure_text(R: Path, bank: Path, eid: str) -> bool:
    if (R / "text" / f"{eid}-q1.txt").exists() or list((R / "text").glob(f"{eid}-q*.txt")):
        return True
    reg = bank / "register.json"
    ex = next((e for e in load_json(reg)["exams"] if e["exam_id"] == eid), None) if reg.exists() else None
    if not ex or not ex["files"].get("o"):
        return False
    folder = (ROOT / ex["files"]["o"]).parent
    if not folder.exists():
        return False
    tmp = R / "_exam"
    tmp.mkdir(exist_ok=True)
    r = subprocess.run([sys.executable, str(ROOT / "scripts/exam/exam_text.py"), str(tmp), str(folder)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False
    (R / "text").mkdir(exist_ok=True)
    for f in (tmp / "text").glob(f"{eid}-*.txt"):
        shutil.copy2(f, R / "text" / f.name)
    return bool(list((R / "text").glob(f"{eid}-q*.txt")))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    run = ToetsRun(R, subjects_opt(argv))
    bank = Path(opt(argv, "--bank")) if opt(argv, "--bank") else run.subjects / run.subject / "examenbank"
    bp = run.blueprint()
    refs: dict[str, list[str]] = {}
    for o in bp["opgaven"]:
        for v in o["vragen"]:
            for c in pattern_codes(v["pattern"]):
                refs.setdefault(c, [])
                for r in v["example_refs"]:
                    if r not in refs[c]:
                        refs[c].append(r)
    (R / "33_examples").mkdir(exist_ok=True)
    (R / "text").mkdir(exist_ok=True)
    missing, n_ok = [], 0
    for code, rs in sorted(refs.items()):
        p = run.pidx.get(code, {})
        L = [f"# Stijlvoorbeelden {code} {p.get('name', '')}", "",
             "*Alleen voor de vorm (vraagstelling, opbouw, puntverdeling). Neem geen context, getallen of zinnen over: "
             "overlap_check.py faalt op elke gedeelde reeks van 8 woorden.*", "",
             f"**Omschrijving:** {p.get('description', '')}  ", f"**Stamvormen:** {' · '.join(p.get('stem_forms', []))}  ",
             f"**Scoring:** {p.get('scoring', '')}", ""]
        for r in rs:
            m = REF.search(r)
            if not m:
                missing.append(r)
                continue
            eid, n = m.group(1), int(m.group(2))
            if not ensure_text(R, bank, eid) or not (R / "text" / f"{eid}-q{n}.txt").exists():
                missing.append(r)
                L += [f"## {eid} vraag {n}", "", "*Examentekst niet beschikbaar (pdf ontbreekt).*", ""]
                continue
            q = read(R / "text" / f"{eid}-q{n}.txt")
            L += [f"## {eid} vraag {n}", "", q, ""]
            for m2 in REF_RE.finditer(q):
                if m2.group(0).lower().startswith(("informatiebron", "bron")):
                    for b in re.findall(r"\d+", m2.group(0)):
                        bt = read(R / "text" / f"{eid}-bron{b}.txt")
                        if bt:
                            L += [f"### informatiebron {b}", "", bt, ""]
            cv = read(R / "text" / f"{eid}-q{n}.cv.txt")
            L += ["### correctievoorschrift", "", cv or "*niet beschikbaar*", ""]
            n_ok += 1
        (R / "33_examples" / f"{code}.md").write_text("\n".join(L), encoding="utf-8")
    run.run["examples_missing"] = sorted(set(run.run.get("examples_missing", [])) | set(missing))
    save_json(R / "run.json", run.run)
    print(f"[exam_examples] {len(refs)} patterns, {n_ok} examples written to 33_examples/; "
          f"{len(missing)} missing: {', '.join(missing) or '–'}")


if __name__ == "__main__":
    main(sys.argv)
