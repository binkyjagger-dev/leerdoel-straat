#!/usr/bin/env python3
"""Extract CvTE exam PDFs into exam units (specs/21 §3–§5).

Usage: exam_text.py <run_dir> <exam_folder> [<exam_folder> ...]

Each exam folder holds `*-o.pdf` (opgaven), `*-c.pdf` (correctievoorschrift) and
optionally `*-b.pdf` (bijlage) and `*-u.pdf` (uitwerkbijlage); a folder without PDFs
is expanded to its subfolders. Copies the PDFs to <run_dir>/input/<exam_id>/, writes
text files to <run_dir>/text/ and a draft <run_dir>/21_exam_units.json whose
`parse_issues` the exam-ingest agent resolves. Existing exams in the units file are
replaced, others kept.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import load_json, save_json  # noqa: E402

LEVELS = {"VW": "vwo", "HA": "havo", "VM": "vmbo"}
CODE_RE = re.compile(r"^(VW|HA|VM)-(\d{4})-a-(\d{2})-(\d)-([ocbu])$", re.I)
FILE_RE = re.compile(r"^([a-z]{2})-(\d{4})-a-(\d{2})-(\d)-([ocbu])\.pdf$", re.I)
PAGE_NO = re.compile(r"^(\d+( / \d+)?|einde|lees verder.*|►+)$")
CV_HEADS = {"Vraag", "Antwoord", "Scores", "Vraag Antwoord", "Vraag Antwoord Scores"}
PER_ITEM = re.compile(r"^per\s+(juist|juiste|goed|correct)", re.I)
SOURCES_RE = re.compile(r"informatiebron(?:nen)?\s+(\d+)(?:\s+(tot en met|t/m|en)\s+(\d+))?", re.I)


def pdf_lines(path: Path, issues: list, exam_id: str, code: str | None) -> tuple[list[str], int]:
    """Text lines of a PDF without page furniture; returns (lines, pages without text)."""
    import pymupdf
    doc = pymupdf.open(path)
    out: list[str] = []
    empty = 0
    for pno, page in enumerate(doc, start=1):
        text = page.get_text()
        if len(text.strip()) < 20 and page.get_images():
            empty += 1
            issues.append({"exam_id": exam_id, "unit_id": None,
                           "issue": f"{path.name} page {pno} has no text layer (OCR needed)"})
        # private-use glyphs are list markers of the CvTE fonts (U+F02D etc.)
        text = re.sub(r"[-]", "-", text)
        lines = [ln.rstrip() for ln in text.splitlines()]
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if code and s.upper().startswith(code.upper()):
                i += 1
                while i < len(lines) and PAGE_NO.match(lines[i].strip() or "x") and lines[i].strip():
                    i += 1
                continue
            if PAGE_NO.match(s) and s.startswith(("lees", "►", "einde")):
                i += 1
                continue
            out.append(lines[i])
            i += 1
    return out, empty


def strip_blank_runs(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if not ln.strip() and (not out or not out[-1].strip()):
            continue
        out.append(ln)
    while out and not out[-1].strip():
        out.pop()
    return out


def parse_sources(text: str) -> list[int]:
    found: set[int] = set()
    for m in SOURCES_RE.finditer(text):
        a = int(m.group(1))
        if m.group(3) and m.group(2).lower() in ("tot en met", "t/m"):
            found.update(range(a, int(m.group(3)) + 1))
        else:
            found.add(a)
            if m.group(3):
                found.add(int(m.group(3)))
    return sorted(found)


def find_files(folder: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for p in sorted(folder.glob("*.pdf")):
        m = FILE_RE.match(p.name)
        if m:
            files[m.group(5).lower()] = p
    return files


def exam_meta(files: dict[str, Path], subject: str) -> dict:
    m = FILE_RE.match(files["o"].name)
    lvl, vak, yy, tv = m.group(1).upper(), m.group(2), m.group(3), m.group(4)
    code = f"{lvl}-{vak}-a-{yy}-{tv}"
    return {"exam_id": f"{LEVELS.get(lvl, lvl.lower())}-20{yy}-tv{tv}", "code": code,
            "level": LEVELS.get(lvl, lvl.lower()), "year": 2000 + int(yy), "tijdvak": int(tv),
            "subject": subject}


def parse_header(lines: list[str]) -> tuple[int | None, int | None]:
    head = " ".join(ln.strip() for ln in lines[:80])
    n = re.search(r"bestaat uit (\d+) vragen", head)
    m = re.search(r"maximaal (\d+) punten", head)
    return (int(n.group(1)) if n else None, int(m.group(1)) if m else None)


def parse_opgaven(lines: list[str], exam_id: str, issues: list) -> list[dict]:
    """Split the opgavenboekje into opgaven and questions (with their context)."""
    opgaven: list[dict] = []
    cur: dict | None = None
    context: list[str] = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        mo = re.match(r"^Opgave (\d+)$", s)
        if mo:
            cur = {"number": int(mo.group(1)), "lines": [], "questions": []}
            opgaven.append(cur)
            context = []
            i += 1
            continue
        mp = re.match(r"^(\d+)p(?:\s+(\d+))?$", s)
        if cur is not None and mp:
            points = int(mp.group(1))
            num = mp.group(2)
            j = i + 1
            if num is None:
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and re.match(r"^\d+$", lines[j].strip()):
                    num = lines[j].strip()
                    j += 1
            if num is None:
                issues.append({"exam_id": exam_id, "unit_id": None,
                               "issue": f"'{s}' without question number (opgave {cur['number']})"})
                i += 1
                continue
            ask: list[str] = []
            while j < len(lines) and not lines[j].strip():
                j += 1
            while j < len(lines) and lines[j].strip():
                ask.append(lines[j].strip())
                j += 1
            cur["questions"].append({"number": int(num), "points": points,
                                     "context": strip_blank_runs(context), "ask": ask})
            cur["lines"] += [lines[k] for k in range(i, j)]
            context = []
            i = j
            continue
        if cur is not None:
            cur["lines"].append(lines[i])
            context.append(lines[i])
        i += 1
    return opgaven


def parse_bijlage(lines: list[str]) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    """Informatiebronnen (number → lines) and formulas (question number → lines)."""
    bronnen: dict[int, list[str]] = {}
    formulas: dict[int, list[str]] = {}
    target: list[str] | None = None
    for ln in lines:
        s = ln.strip()
        mb = re.match(r"^Informatiebron (\d+)$", s)
        mf = re.match(r"^Voor beantwoording van vraag (\d+)", s)
        if mb:
            target = bronnen.setdefault(int(mb.group(1)), [])
            continue
        if mf:
            target = formulas.setdefault(int(mf.group(1)), [])
        if target is not None:
            target.append(ln)
    return ({k: strip_blank_runs(v) for k, v in bronnen.items()},
            {k: strip_blank_runs(v) for k, v in formulas.items()})


def cv_entries(lines: list[str]) -> dict[int, dict]:
    """Correctievoorschrift chapter 'Beoordelingsmodel' → question number → entry."""
    start = max((i for i, ln in enumerate(lines) if "Beoordelingsmodel" in ln), default=0)
    end = len(lines)
    for i in range(len(lines) - 1, start, -1):
        if re.match(r"^\s*5\s+Aanleveren", lines[i]):
            end = i
            break
    body = [ln for ln in lines[start + 1:end] if ln.strip() not in CV_HEADS]
    entries: dict[int, dict] = {}
    cur: dict | None = None
    i = 0
    while i < len(body):
        s = body[i].strip()
        if re.match(r"^\d+$", s):
            j = i + 1
            while j < len(body) and not body[j].strip():
                j += 1
            mm = re.match(r"^maximumscore (\d+)$", body[j].strip()) if j < len(body) else None
            if mm:
                cur = {"max": int(mm.group(1)), "lines": []}
                entries[int(s)] = cur
                i = j + 1
                continue
        if re.match(r"^Opgave \d+$", s):
            i += 1
            continue
        if cur is not None:
            cur["lines"].append(body[i])
        i += 1
    return entries


def scorepunten(entry: dict) -> tuple[str, list[dict], list[str], str | None]:
    """(scoring, [{points, text}], notes, issue) for one correctievoorschrift entry."""
    lines = [ln.strip() for ln in entry["lines"]]
    if "•" in lines:
        # An "of" line ends the route once the bullets so far reach the maximum score
        # (a complete alternative route follows, 2025-I q3); before that it introduces an
        # alternative answer for the current bullet only (2026-I q12, q16) -> note.
        sps: list[dict] = []
        notes: list[str] = []
        seg: list[str] | None = None
        alt: list[str] | None = None
        issue = None

        def close() -> None:
            nonlocal seg, issue
            if seg is None:
                return
            pts_idx = max((k for k, s in enumerate(seg) if re.match(r"^[1-9]$", s)), default=None)
            if pts_idx is None:
                issue = f"bullet {len(sps) + 1} without point value"
            sps.append({"points": int(seg[pts_idx]) if pts_idx is not None else 1,
                        "text": " ".join(s for k, s in enumerate(seg)
                                         if s and k != pts_idx and not re.match(r"^\w+ deelscore:$", s))})
            seg = None

        k = 0
        while k < len(lines):
            s = lines[k]
            if re.match(r"^Opmerkingen?$", s):
                close()
                notes.append(" ".join(x for x in lines[k:] if x))
                break
            if s == "•":
                close()
                if alt:
                    notes.append("of: " + " ".join(alt))
                alt = None
                seg = []
            elif s == "of":
                done = sum(sp["points"] for sp in sps) + (1 if seg is not None else 0)
                if done >= entry["max"]:
                    close()
                    notes.append("of: " + " ".join(x for x in lines[k + 1:] if x))
                    break
                close()
                alt = []
            elif alt is not None:
                if s and not re.match(r"^[1-9]$", s):
                    alt.append(s)
            elif seg is not None:
                seg.append(s)
            k += 1
        else:
            close()
            if alt:
                notes.append("of: " + " ".join(alt))
        return "bullet", sps, notes, issue
    route_end = len(lines)
    for k, s in enumerate(lines):
        if s == "of" or re.match(r"^Opmerkingen?$", s):
            route_end = k
            break
    route, rest = lines[:route_end], lines[route_end:]
    notes = [" ".join(x for x in rest if x)] if any(rest) else []
    for k, s in enumerate(route):
        if PER_ITEM.match(s):
            nxt = next((x for x in route[k + 1:] if x), None)
            val = int(nxt) if nxt and re.match(r"^[1-9]$", nxt) else 1
            text = " ".join(x for x in route[:k + 1] if x)
            if entry["max"] % val:
                return "per_item", [{"points": entry["max"], "text": text}], notes, \
                    f"per-item value {val} does not divide maximumscore {entry['max']}"
            return "per_item", [{"points": val, "text": text} for _ in range(entry["max"] // val)], notes, None
    text = " ".join(x for x in route if x)
    return "whole", [{"points": entry["max"], "text": text}], notes, None


def write(run_dir: Path, name: str, lines: list[str]) -> str:
    ref = f"text/{name}"
    (run_dir / ref).write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return ref


def ingest_exam(run_dir: Path, folder: Path, subject: str) -> tuple[dict, list[dict], list[dict]]:
    files = find_files(folder)
    issues: list[dict] = []
    if "o" not in files or "c" not in files:
        raise SystemExit(f"[exam_text] {folder}: need *-o.pdf and *-c.pdf, found {sorted(files)}")
    meta = exam_meta(files, subject)
    eid, code = meta["exam_id"], meta["code"]
    dest = run_dir / "input" / eid
    dest.mkdir(parents=True, exist_ok=True)
    meta["files"], meta["source_files"] = {}, {}
    for part, p in files.items():
        shutil.copy2(p, dest / p.name)
        meta["files"][part] = (dest / p.name).relative_to(run_dir).as_posix()
        try:
            meta["source_files"][part] = p.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            meta["source_files"][part] = p.as_posix()
    o_lines, o_empty = pdf_lines(files["o"], issues, eid, f"{code}-o")
    c_lines, c_empty = pdf_lines(files["c"], issues, eid, f"{code}-c")
    b_lines, b_empty = pdf_lines(files["b"], issues, eid, f"{code}-b") if "b" in files else ([], 0)
    meta["n_questions"], meta["max_score"] = parse_header(o_lines)
    meta["syllabus_note"] = None
    meta["text_extraction"] = "text" if not (o_empty or c_empty or b_empty) else "mixed"
    if meta["n_questions"] is None or meta["max_score"] is None:
        issues.append({"exam_id": eid, "unit_id": None, "issue": "header counts (vragen/punten) not found"})

    bronnen, formulas = parse_bijlage(b_lines)
    for n, blines in bronnen.items():
        write(run_dir, f"{eid}-bron{n}.txt", blines)
    formula_refs = {q: write(run_dir, f"{eid}-formule-q{q}.txt", fl) for q, fl in formulas.items()}

    entries = cv_entries(c_lines)
    units: list[dict] = []
    seen_q: set[int] = set()
    for og in parse_opgaven(o_lines, eid, issues):
        oid = f"{eid}-o{og['number']}"
        otext = strip_blank_runs(og["lines"])
        units.append({"unit_id": oid, "kind": "opgave", "exam_id": eid, "number": og["number"],
                      "title": next((s.strip() for s in otext if s.strip() and not s.strip().startswith("Bij deze opgave")), "")[:80],
                      "sources": parse_sources("\n".join(otext)),
                      "text_ref": write(run_dir, f"{eid}-o{og['number']}.txt", [f"Opgave {og['number']}", ""] + otext)})
        for q in og["questions"]:
            n = q["number"]
            qid = f"{eid}-q{n}"
            if n in seen_q:
                issues.append({"exam_id": eid, "unit_id": qid, "issue": f"question {n} found twice"})
            seen_q.add(n)
            qlines = (["[context]"] + q["context"] + [""] if q["context"] else []) + \
                     ["[vraag]", f"{q['points']}p {n} " + " ".join(q["ask"])]
            entry = entries.get(n)
            cv_ref, cv_max, notes = None, None, []
            if entry is None:
                issues.append({"exam_id": eid, "unit_id": qid, "issue": "no correctievoorschrift entry"})
            else:
                cv_max = entry["max"]
                cv_ref = write(run_dir, f"{eid}-q{n}.cv.txt",
                               [f"{n} maximumscore {cv_max}"] + strip_blank_runs(entry["lines"]))
            units.append({"unit_id": qid, "kind": "question", "exam_id": eid, "opgave_id": oid,
                          "number": n, "points": q["points"],
                          "text_ref": write(run_dir, f"{eid}-q{n}.txt", qlines),
                          "sources": parse_sources("\n".join(q["context"] + q["ask"])),
                          "cv_max": cv_max, "cv_ref": cv_ref, "cv_notes": notes,
                          "formula_ref": formula_refs.get(n)})
            if entry is None:
                continue
            scoring, sps, notes, issue = scorepunten(entry)
            units[-1]["cv_notes"] = notes
            if issue:
                issues.append({"exam_id": eid, "unit_id": qid, "issue": issue})
            for k, sp in enumerate(sps, start=1):
                units.append({"unit_id": f"{qid}-s{k}", "kind": "scorepunt", "exam_id": eid,
                              "question_id": qid, "seq": k, "points": sp["points"],
                              "scoring": scoring, "text": sp["text"]})
    for n in sorted(set(entries) - seen_q):
        issues.append({"exam_id": eid, "unit_id": f"{eid}-q{n}",
                       "issue": f"correctievoorschrift has question {n} but the opgavenboekje parse did not find it"})
    return meta, units, issues


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    run = load_json(run_dir / "run.json") if (run_dir / "run.json").exists() else {}
    subject = run.get("subject", "onbekend")
    folders: list[Path] = []
    for a in argv[2:]:
        p = Path(a)
        folders += [p] if list(p.glob("*.pdf")) else sorted(d for d in p.iterdir() if d.is_dir() and list(d.glob("*.pdf")))
    (run_dir / "text").mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "21_exam_units.json"
    data = load_json(out_path) if out_path.exists() else {"run_id": run.get("run_id", run_dir.name),
                                                         "exams": [], "units": [], "parse_issues": []}
    for folder in folders:
        meta, units, issues = ingest_exam(run_dir, folder, subject)
        eid = meta["exam_id"]
        data["exams"] = [e for e in data["exams"] if e["exam_id"] != eid] + [meta]
        data["units"] = [u for u in data["units"] if u["exam_id"] != eid] + units
        data["parse_issues"] = [x for x in data["parse_issues"] if x["exam_id"] != eid] + issues
        nq = sum(1 for u in units if u["kind"] == "question")
        ns = sum(1 for u in units if u["kind"] == "scorepunt")
        print(f"[exam_text] {eid}: header {meta['n_questions']} vragen / {meta['max_score']} p; "
              f"parsed {nq} questions, {ns} scorepunten; {len(issues)} parse issues")
    save_json(out_path, data)


if __name__ == "__main__":
    main(sys.argv)
