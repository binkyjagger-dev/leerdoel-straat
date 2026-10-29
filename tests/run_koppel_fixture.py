#!/usr/bin/env python3
"""Exercise the methode-straat scripts on the koppel fixture. Usage: python tests/run_koppel_fixture.py"""
from __future__ import annotations
import json, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
PY = sys.executable
def run(label, *args, allow_fail=False):
    print(f"== {label}")
    r = subprocess.run([PY, *args], cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
    print(r.stdout, end="")
    if r.returncode != 0 and not allow_fail:
        print(r.stderr, end=""); print(f"!! FAILED: {label}"); return False
    return True
W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"')
def make_docx(path):
    """Workbook in the specs/11 §2.2 shape: exercise heading with icon, a table, auto-numbered a/b twice."""
    li = lambda num, t: f'<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num}"/></w:numPr></w:pPr><w:r><w:t>{t}</w:t></w:r></w:p>'
    p = lambda t: f'<w:p><w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'
    icon = '<w:p><w:r><w:t>1-1 (§ 1.1)</w:t></w:r><w:r><w:tab/><w:drawing><a:blip r:embed="rId9"/></w:drawing></w:r></w:p>'
    tbl = '<w:tbl><w:tr><w:tc>' + p("Kas") + '</w:tc><w:tc>' + p("€ 10") + '</w:tc></w:tr></w:tbl>'
    body = icon + p("Gegeven:") + tbl + li(1, "Bereken A.") + li(1, "Bereken B.") + p("1-2 (§ 1.2)") + li(2, "Leg uit C.") + p(" ")
    num = (f'<w:numbering {W_NS}><w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/>'
           '<w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>'
           '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
           '<w:num w:numId="2"><w:abstractNumId w:val="0"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num></w:numbering>')
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId9" Type="image" Target="media/image1.png"/></Relationships>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f'<w:document {W_NS}><w:body>{body}</w:body></w:document>')
        z.writestr("word/numbering.xml", num)
        z.writestr("word/_rels/document.xml.rels", rels)
        z.writestr("word/media/image1.png", b"png")
def check(label, cond):
    print(f"   {'ok ' if cond else 'NOK'} {label}")
    return bool(cond)
def extend_scenario(prev, s):
    """--extend (specs/13 §5): the finished fixture run plus a new chapter H2 with one paragraph."""
    ok = True
    rj = json.loads((prev / "run.json").read_text(encoding="utf-8"))
    rj["status"] = "done"; (prev / "run.json").write_text(json.dumps(rj), encoding="utf-8")
    x = prev.parent / "ext-run"
    ok &= run("extend: prepare", f"{s}/koppel_extend.py", "prepare", str(x), str(prev))
    q = "Een uitkomst tussen 0 en -1 noemen we inelastisch; is de uitkomst kleiner dan -1, dan noemen we de vraag elastisch."
    (x / "text" / "H2.1.txt").write_text("2.1 Elasticiteit interpreteren\n\nDe prijselasticiteit zegt hoe sterk de vraag reageert. " + q + "\n", encoding="utf-8")
    meth = json.loads((x / "11_method_units.prev.json").read_text(encoding="utf-8"))["method"]
    new = {"method": {**meth, "files": ["input/ext/book/"]},
           "units": [{"unit_id": "H2", "parent_id": None, "kind": "hoofdstuk", "code": "2", "title": "Elasticiteit"},
                     {"unit_id": "H2.1", "parent_id": "H2", "kind": "paragraaf", "code": "2.1", "title": "Elasticiteit interpreteren",
                      "text_ref": "text/H2.1.txt", "concepts": ["prijselasticiteit", "inelastisch", "elastisch"]}]}
    (x / "11_method_units.new.json").write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    ok &= run("extend: merge-units", f"{s}/koppel_extend.py", "merge-units", str(x))
    units = json.loads((x / "11_method_units.json").read_text(encoding="utf-8"))["units"]
    ok &= check("new paragraph ordered after the old ones", next(u["order"] for u in units if u["unit_id"] == "H2.1") == 4)
    ok &= run("extend: validate_method", f"{s}/validate_method.py", str(x))
    ok &= run("extend: candidates", f"{s}/candidates.py", str(x))
    ok &= run("extend: todo", f"{s}/koppel_extend.py", "todo", str(x))
    todo = json.loads((x / "12_extend_todo.json").read_text(encoding="utf-8"))
    ok &= check("todo: H2.1 is the only new paragraph", todo["new_paragraphs"] == ["H2.1"])
    # judges: H2.1 explains D1.2-01-b, every other candidate none; delta pairs on old paragraphs none
    cand = json.loads((x / "12_candidates.json").read_text(encoding="utf-8"))
    union = {c["criterion_id"] for p in cand["per_paragraph"] if p["unit_id"] == "H2.1" for c in p["criteria"]}
    union |= {pc["criterion_id"] for pc in cand["per_criterion"] for c in pc["candidates"] if c["unit_id"] == "H2.1"}
    union.add("D1.2-01-b")
    jd = lambda c, t, qq=None: {"criterion_id": c, "treatment": t, "quote": qq, "quote_page": None, "second_quote": None, "aspect": None, "reason": None}
    for j in "AB":
        (x / f"13_judgements.{j}" / "H2.1.json").write_text(json.dumps({"judge": j, "unit_id": "H2.1", "judgements":
            [jd(c, "explains", q) if c == "D1.2-01-b" else jd(c, "none") for c in sorted(union)]}, ensure_ascii=False), encoding="utf-8")
        for uid, crits in todo["delta"].items():
            (x / f"13_judgements.{j}" / f"{uid}.ext.json").write_text(json.dumps({"judge": j, "unit_id": uid,
                "judgements": [jd(c, "none") for c in crits]}), encoding="utf-8")
    same = all((prev / f"13_judgements.{j}" / f.name).read_bytes() == f.read_bytes()
               for j in "AB" for f in (x / f"13_judgements.{j}").glob("H1.?.json"))
    ok &= check("judgements of the previous run reused unchanged", same)
    ok &= run("extend: gradation", f"{s}/gradation.py", str(x))
    ok &= run("extend: check_mappings", f"{s}/check_mappings.py", str(x))
    links = json.loads((x / "14_mappings.json").read_text(encoding="utf-8"))["links"]
    ok &= check("new link D1.2-01-b x H2.1 present", any(l["criterion_id"] == "D1.2-01-b" and l["unit_id"] == "H2.1" for l in links))
    (x / "15_verification.ext.json").write_text(json.dumps({"links": [{"criterion_id": "D1.2-01-b", "unit_id": "H2.1", "verdict": "pass",
        "treatment_should_be": None, "confidence_adjust": None, "reason": "fixture"}], "missing_links": [], "gradation_findings": []}), encoding="utf-8")
    ok &= run("extend: merge-verification", f"{s}/koppel_extend.py", "merge-verification", str(x))
    ok &= run("extend: check_mappings --verification", f"{s}/check_mappings.py", str(x), "--verification", "15_verification.json")
    ok &= run("extend: merge-verification part B", f"{s}/koppel_extend.py", "merge-verification", str(x), "--part", "B")
    ok &= run("extend: ex_candidates", f"{s}/ex_candidates.py", str(x))
    ok &= run("extend: ex_merge", f"{s}/ex_merge.py", str(x))
    ok &= run("extend: check_ex_mappings --verification", f"{s}/check_ex_mappings.py", str(x), "--verification", "19_ex_verification.json")
    ok &= run("extend: export", f"{s}/export_mappings.py", str(x))
    sample = (x / "output" / "steekproef.md").read_text(encoding="utf-8")
    ok &= check("extend sample only from the new paragraph", "× 2.1 " in sample and "× 1." not in sample)
    # teacher review (specs/14 §5.1): reject one old link, correct the new one to mentions, one entry on a non-link
    links = json.loads((x / "14_mappings.json").read_text(encoding="utf-8"))["links"]
    rej = next(l for l in links if l["unit_id"] != "H2.1")
    rv = lambda c, u, v, **k: {"criterion_id": c, "unit_id": u, "verdict": v, "note": "fixture", "source": "steekproef", "by": "user", "at": "2026-10-28", **k}
    (x / "16_teacher_review.json").write_text(json.dumps({"reviews": [rv(rej["criterion_id"], rej["unit_id"], "reject"),
        rv("D1.2-01-b", "H2.1", "correct", treatment="mentions"), rv("D1.2-01-b", "H1.1", "confirm")]}), encoding="utf-8")
    ok &= run("teacher review: gradation", f"{s}/gradation.py", str(x))
    mp = json.loads((x / "14_mappings.json").read_text(encoding="utf-8"))
    idx = {(l["criterion_id"], l["unit_id"]): l for l in mp["links"]}
    ok &= check("rejected link removed and kept for audit", (rej["criterion_id"], rej["unit_id"]) not in idx
                and any(t["criterion_id"] == rej["criterion_id"] for t in mp["teacher_rejected"]))
    cor = idx.get(("D1.2-01-b", "H2.1"))
    ok &= check("corrected link: mentions -> noemt, confirmed", cor and cor["gradation"] == "noemt" and cor["status"] == "confirmed")
    ok &= run("teacher review: check_mappings --verification", f"{s}/check_mappings.py", str(x), "--verification", "15_verification.json")
    sp = x / "output" / "steekproef.md"
    sp.write_text(sp.read_text(encoding="utf-8").replace("|  |  |  |  |", "|J|N|J|J|", 1), encoding="utf-8")
    ok &= run("teacher review: export", f"{s}/export_mappings.py", str(x))
    ok &= check("filled-in sample kept, not overwritten", "|J|N|J|J|" in (x / "output" / "steekproef.ingevuld.md").read_text(encoding="utf-8"))
    ok &= check("reviewed link not sampled again", "× 2.1 " not in (x / "output" / "steekproef.md").read_text(encoding="utf-8"))
    rx = json.loads((x / "run.json").read_text(encoding="utf-8")); rx["scope_exclude_groups"] = ["D1.2-01"]
    (x / "run.json").write_text(json.dumps(rx), encoding="utf-8")
    ok &= run("candidates with scope_exclude_groups", f"{s}/candidates.py", str(x))
    sc = json.loads((x / "12_candidates.json").read_text(encoding="utf-8"))["scope_criteria"]
    ok &= check("excluded group D1.2-01 not in scope, D1.1 still is", not any(c.startswith("D1.2-01") for c in sc) and "D1.1-01-a" in sc)
    ok &= run("extend: prepare again (must fail)", f"{s}/koppel_extend.py", "prepare", str(x), str(prev), allow_fail=True)
    return ok


def main():
    r = Path(tempfile.mkdtemp()) / "run"; shutil.copytree(ROOT / "tests" / "fixtures" / "koppel", r)
    s = "scripts/mapping"; ok = True
    ok &= run("validate_method", f"{s}/validate_method.py", str(r))
    ok &= run("candidates", f"{s}/candidates.py", str(r))
    ok &= run("gradation", f"{s}/gradation.py", str(r))
    ok &= run("check_mappings", f"{s}/check_mappings.py", str(r))
    ok &= run("check_mappings --verification", f"{s}/check_mappings.py", str(r), "--verification", "15_verification.json")
    ok &= run("export", f"{s}/export_mappings.py", str(r))
    ok &= run("compare_baseline", f"{s}/compare_baseline.py", str(r), str(r / "baseline.csv"))
    # part B
    ok &= run("ex_candidates", f"{s}/ex_candidates.py", str(r))
    ok &= run("ex_merge", f"{s}/ex_merge.py", str(r))
    ok &= run("check_ex_mappings", f"{s}/check_ex_mappings.py", str(r))
    ok &= run("check_ex_mappings --verification", f"{s}/check_ex_mappings.py", str(r), "--verification", "19_ex_verification.json")
    ok &= run("check_ex_mappings --verification (again, idempotent)", f"{s}/check_ex_mappings.py", str(r), "--verification", "19_ex_verification.json")
    shutil.copytree(r / "_repair" / "18_ex_judgements.R", r / "18_ex_judgements.R")
    ok &= run("ex_merge (with repair R)", f"{s}/ex_merge.py", str(r))
    ok &= run("check_ex_mappings --verification (after repair)", f"{s}/check_ex_mappings.py", str(r), "--verification", "19_ex_verification.json")
    ok &= run("export_exercises", f"{s}/export_exercises.py", str(r))
    ok &= run("export (after part B)", f"{s}/export_mappings.py", str(r))
    ok &= extend_scenario(r, s)
    # ingest adapters for page images + workbook (specs/11 §2.2)
    a = r.parent / "adapters"; (a / "book").mkdir(parents=True)
    for n in ("H1_1.1_10.png", "H1_1.1_2.png", "notes.txt"):
        (a / "book" / n).write_bytes(b"x")
    ok &= run("ocr_images --no-ocr", f"{s}/ocr_images.py", str(a / "book"), str(a / "pages"), "--no-ocr", allow_fail=True)
    pj = json.loads((a / "pages" / "pages.json").read_text(encoding="utf-8"))
    ok &= check("images only, natural order", [f["file"] for f in pj["files"]] == ["H1_1.1_2.png", "H1_1.1_10.png"])
    ok &= check("unresolved without OCR", pj["unresolved_pages"] == [1, 2])
    make_docx(a / "werkboek.docx")
    ok &= run("docx_text", f"{s}/docx_text.py", str(a / "werkboek.docx"), str(a / "wb"))
    doc = (a / "wb" / "document.txt").read_text(encoding="utf-8").splitlines()
    print("   " + " ‖ ".join(doc))
    ok &= check("icon marked inline", doc[0] == "1-1 (§ 1.1)\t[afbeelding: media/image1.png]")
    ok &= check("table row", "| Kas | € 10 |" in doc)
    ok &= check("list letters a, b", "a. Bereken A." in doc and "b. Bereken B." in doc)
    ok &= check("startOverride restarts at a", "a. Leg uit C." in doc)
    ok &= check("blank paragraph dropped", doc[-1] == "a. Leg uit C.")
    ok &= check("media extracted", (a / "wb" / "media" / "image1.png").exists())
    print("\nOutput:", sorted(p.name for p in (r / "output").iterdir()))
    print("\nRESULT:", "OK" if ok else "FAILED"); return 0 if ok else 1
if __name__ == "__main__": sys.exit(main())
