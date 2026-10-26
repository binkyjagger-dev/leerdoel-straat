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
