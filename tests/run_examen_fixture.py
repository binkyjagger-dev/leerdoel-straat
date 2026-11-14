#!/usr/bin/env python3
"""Exercise the examen-straat scripts on the examen fixture. Usage: python tests/run_examen_fixture.py

Builds small exam PDFs (opgaven, correctievoorschrift over three pages, bijlage) from
tests/fixtures/examen/pdf_src.json, then runs ingest → candidates → merge → checks → verification →
repair → bank → export in a temp dir, with checks on the outcome.
"""
from __future__ import annotations
import csv, html, json, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
PY = sys.executable
E = "vwo-2030-tv1"


def run(label, *args, expect_fail=False):
    print(f"== {label}")
    r = subprocess.run([PY, "-X", "utf8", *args], cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
    print(r.stdout, end="")
    failed = r.returncode != 0
    if failed != expect_fail:
        print(r.stderr, end="")
        print(f"!! {'FAILED' if failed else 'UNEXPECTEDLY PASSED'}: {label}")
        return False
    return True


def check(label, cond):
    print(f"   {'ok ' if cond else 'NOK'} {label}")
    return bool(cond)


def make_pdfs(src: dict, folder: Path) -> None:
    import pymupdf
    folder.mkdir(parents=True, exist_ok=True)
    for name, pages in src["files"].items():
        doc = pymupdf.open()
        for lines in pages:
            page = doc.new_page()
            body = "".join(f"<p style='margin:0'>{html.escape(l) if l.strip() else '&nbsp;'}</p>" for l in lines)
            page.insert_htmlbox(page.rect + (50, 50, -50, -50), body, css="p{font-family:sans-serif;font-size:9px}")
        doc.save(folder / name)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def by_sp(r):
    return {l["scorepunt_id"].replace(E + "-", ""): l for l in load(r / "24_mappings.json")["links"]}


def sources_cases(tmp: Path) -> bool:
    """Question `sources` / `sources_from` (specs/21 §3): every form a question can name bronnen in,
    the opgave fallback, and never from the correctievoorschrift."""
    furn = ["VW-9999-a-31-1-o", "1 / 1", "einde"]
    o = ["VW-9999-a-31-1-o", "Examen VWO", "Dit examen bestaat uit 7 vragen.", "Voor dit examen zijn maximaal 7 punten te behalen.", " ",
         "Opgave 1", " ", "Bij deze opgave horen de informatiebronnen 1 tot en met 4.", " ", "Camping Vogelhof heeft 280 standplaatsen.", " ",
         "1p", "1", "Bereken de omzet (zie informatiebron 2).", " ",
         "De kosten van het veld staan in de bijlage (zie informatiebronnen 2, 3 en", "4).", " ",
         "1p", "2", "Bereken de totale kosten.", " ",
         "1p", "3", "Bereken de winst (zie informatiebronnen 1 tot en met 3).", " ",
         "1p", "4", "Vergelijk de tarieven (zie informatiebron 3 en 4).", " ",
         "Zonder herinrichting is de bijdrage aan het resultaat € 115.000 voordelig.", " ",
         "1p", "5", "Analyseer of de eigenaren het veld herinrichten.", " ",
         "Opgave 2", " ", "Een nieuwe camping wordt opgericht.", " ",
         "1p", "6", "Noem een geschikte rechtsvorm.", " ",
         "1p", "7", "Bereken de prijs per nacht (zie informatiebronnen 1 t/m 2).", " "] + furn
    c = ["VW-9999-a-31-1-c", "4 Beoordelingsmodel", "Vraag", "Antwoord", "Scores", "Opgave 1"]
    for n in range(1, 8):
        c += [str(n), "maximumscore 1",
              "eenmanszaak (zie informatiebron 1 en 4)" if n == 6 else f"antwoord {n} met informatiebron 4", " "]
    c += ["5 Aanleveren scores", "VW-9999-a-31-1-c", "1", "einde"]
    b = ["VW-9999-a-31-1-b", "Bijlage VWO"] + [x for n in range(1, 5) for x in (f"Informatiebron {n}", " ", f"Tabel {n}", " ")] + \
        ["VW-9999-a-31-1-b", "1 / 1", "einde"]
    ex, r = tmp / "src_exams", tmp / "src_run"
    make_pdfs({"files": {"vw-9999-a-31-1-o.pdf": [o], "vw-9999-a-31-1-c.pdf": [c], "vw-9999-a-31-1-b.pdf": [b]}}, ex / "2031 TV1")
    r.mkdir()
    (r / "run.json").write_text(json.dumps({"run_id": "src", "subject": "fixturevak"}), encoding="utf-8")
    ok = run("exam_text (bron forms)", "scripts/exam/exam_text.py", str(r), str(ex))
    ok &= run("validate_exam (bron forms)", "scripts/exam/validate_exam.py", str(r))
    q = {x["number"]: (x["sources"], x["sources_from"]) for x in load(r / "21_exam_units.json")["units"] if x["kind"] == "question"}
    ok &= check("'informatiebron 2' -> [2]; the opgave's 'horen' sentence in q1's context does not count",
                q[1] == ([2], "question"))
    ok &= check("'informatiebronnen 2, 3 en' + line break + '4' in the context -> [2, 3, 4]", q[2] == ([2, 3, 4], "question"))
    ok &= check("'informatiebronnen 1 tot en met 3' -> [1, 2, 3]", q[3] == ([1, 2, 3], "question"))
    ok &= check("'zie informatiebron 3 en 4' -> [3, 4]", q[4] == ([3, 4], "question"))
    ok &= check("no bron named -> the opgave's 'horen de informatiebronnen 1 tot en met 4', sources_from opgave",
                q[5] == ([1, 2, 3, 4], "opgave"))
    ok &= check("opgave without 'horen' sentence -> [] (question); bronnen in the cv are never used", q[6] == ([], "question"))
    ok &= check("'informatiebronnen 1 t/m 2' -> [1, 2]", q[7] == ([1, 2], "question"))
    return ok


def main():
    tmp = Path(tempfile.mkdtemp())
    r = tmp / "run"
    shutil.copytree(ROOT / "tests" / "fixtures" / "examen", r)
    src = load(r / "pdf_src.json")
    exams = tmp / "examens"
    make_pdfs(src, exams / src["folder"])
    s, bank, ok = "scripts/exam", tmp / "bank", True

    ok &= run("exam_text", f"{s}/exam_text.py", str(r), str(exams))
    ok &= run("validate_exam", f"{s}/validate_exam.py", str(r))
    u = load(r / "21_exam_units.json")
    sps = [x for x in u["units"] if x["kind"] == "scorepunt"]
    ok &= check("3 questions, 6 scorepunten (bullet 3, per_item 2, whole 1)",
                sum(x["kind"] == "question" for x in u["units"]) == 3 and
                [x["scoring"] for x in sps] == ["bullet"] * 3 + ["per_item"] * 2 + ["whole"])
    ok &= check("€ and é survive extraction; 'of' route goes to cv_notes",
                "€ 4.000" in sps[0]["text"] and
                any("prijselasticiteit" in n for x in u["units"] if x["kind"] == "question" for n in x["cv_notes"]))
    ok &= check("Opmerking(en) never inside a scorepunt text", not any("Opmerking" in x["text"] for x in sps))
    ok &= check("informatiebron 1 found for opgave 1", u["units"][0]["sources"] == [1] and (r / f"text/{E}-bron1.txt").exists())
    q1 = next(x for x in u["units"] if x["unit_id"] == f"{E}-q1")
    ok &= check("q1 names no bron itself -> opgave's 'hoort informatiebron 1' (sources_from opgave)",
                q1["sources"] == [1] and q1["sources_from"] == "opgave")
    ok &= sources_cases(tmp)

    ok &= run("exam_candidates", f"{s}/exam_candidates.py", str(r))
    cand = {x["scorepunt_id"]: x["candidates"] for x in load(r / "22_candidates.json")["per_scorepunt"]}
    ok &= check("q1-s1 top candidate is the omzet criterion", cand[f"{E}-q1-s1"][0]["criterion_id"] == "X1.1-01-a")

    ok &= run("exam_merge", f"{s}/exam_merge.py", str(r))
    ok &= run("check_exam_mappings", f"{s}/check_exam_mappings.py", str(r))
    m = by_sp(r)
    ok &= check("confidence: q1-s1 high, q1-s2 medium (quote B invalid), q1-s3 medium (bloom differs), q2-s2 low",
                [m[k]["confidence"] for k in ("q1-s1", "q1-s2", "q1-s3", "q2-s2")] == ["high", "medium", "medium", "low"])
    ok &= check("q1-s3 bloom A analyseren / B begrijpen → begrijpen (verb table)", m["q1-s3"]["bloom"] == "begrijpen")
    ok &= check("q3-s1 unlinked (buiten huidige syllabus)", m["q3-s1"]["criterion_id"] is None and
                any(f["finding"] == "buiten huidige syllabus" for f in load(r / "24_mappings.json")["findings"]))
    ok &= check("also_touches kept", m["q1-s1"]["also_touches"] == ["X1.1-01-b"])

    ok &= run("check --verification", f"{s}/check_exam_mappings.py", str(r), "--verification", "25_verification.json")
    ok &= run("check --verification (again, idempotent)", f"{s}/check_exam_mappings.py", str(r), "--verification", "25_verification.json")
    m = by_sp(r)
    ok &= check("verdicts applied; confidence_adjust up on q1-s3", m["q1-s1"]["verifier"] == "pass" and m["q1-s3"]["confidence"] == "high")

    shutil.copytree(r / "_repair" / "23_judgements.R", r / "23_judgements.R")
    ok &= run("exam_merge (with repair R)", f"{s}/exam_merge.py", str(r))
    ok &= run("check --verification (after repair)", f"{s}/check_exam_mappings.py", str(r), "--verification", "25_verification.json")
    m = by_sp(r)
    ok &= check("R keeps q2-s2 linked and replaces B → high", m["q2-s2"]["criterion_id"] == "X1.2-01-a" and m["q2-s2"]["confidence_judged"] == "high")
    ok &= check("R without criterion keeps q3-s1 unlinked", m["q3-s1"]["criterion_id"] is None)

    ok &= run("exam_sample", f"{s}/exam_sample.py", str(r))
    sample = (r / "output" / "steekproef.md").read_text(encoding="utf-8")
    ok &= check("sample: all 5 linked scorepunten (4 high + 1 medium), with the scorepunt line",
                sample.count("\n## ") == 5 and "2.000 x € 2 = € 4.000" in sample)

    ok &= run("bank_add", f"{s}/bank_add.py", str(r), "--bank", str(bank))
    ok &= run("bank_export", f"{s}/bank_export.py", "fixturevak", "--bank", str(bank))
    out = bank / "output"
    rows = list(csv.reader((out / "punten_per_criterium.csv").open(encoding="utf-8-sig"), delimiter=";"))
    col = rows[0].index(f"{E}_punten")
    ok &= check("criterion column sums to 6, 1 point outside the syllabus",
                sum(int(x[col]) for x in rows[1:]) == 6 and rows[-1][0] == "buiten huidige syllabus" and rows[-1][col] == "1")
    idx = list(csv.reader((out / "opzoekindex.csv").open(encoding="utf-8-sig"), delimiter=";"))
    ok &= check("lookup index: 5 linked scorepunten + 1 'raakt ook' row, sorted by criterion", len(idx) == 7 and
                [x[0] for x in idx[1:]] == ["X1.1-01-a", "X1.1-01-b", "X1.1-01-b", "X1.1-01-b", "X1.2-01-a", "X1.2-01-a"])
    touch = [x for x in idx[1:] if x[16] == "raakt ook"]
    ok &= check("raakt ook: X1.1-01-b via q1-s1, 0 points, linked criterion named",
                len(touch) == 1 and touch[0][0] == "X1.1-01-b" and touch[0][10] == "0" and touch[0][14] == "X1.1-01-a")
    ok &= check("per criterion: raakt_ook column counts X1.1-01-b once",
                next(x for x in rows if x[0] == "X1.1-01-b")[rows[0].index(f"{E}_raakt_ook")] == "1")
    dom = list(csv.reader((out / "punten_per_domein.csv").open(encoding="utf-8-sig"), delimiter=";"))
    ok &= check("domein X has 5 points", any(x[0] == "domein" and x[1] == "X" and x[3] == "5" for x in dom))
    ok &= check("bevindingen: X1.2-01-b never tested", "X1.2-01-b" in (out / "bevindingen.md").read_text(encoding="utf-8")
                .split("## nooit getoetst")[1])
    ok &= check("bank keeps its own criteria copy", (bank / "criteria.json").exists() and (bank / "source_units.json").exists())

    # domein-A skill points get their own row (bedrijfsecon-047, specs/25 §3)
    bank_a = tmp / "bank_skill"; shutil.copytree(bank, bank_a)
    lf = bank_a / "links" / f"{E}.json"; lj = load(lf)
    for sp in lj["scorepunten"]:
        if sp["criterion_id"] is None:
            sp["note"] = "Rekenvaardigheid uit domein A (geen criteria), geen vervallen stof"
    lf.write_text(json.dumps(lj, ensure_ascii=False), encoding="utf-8")
    ok &= run("bank_export (domein-A skill note)", f"{s}/bank_export.py", "fixturevak", "--bank", str(bank_a))
    rows_a = list(csv.reader((bank_a / "output" / "punten_per_criterium.csv").open(encoding="utf-8-sig"), delimiter=";"))
    ok &= check("skill point in 'vaardigheid domein A', 0 outside, column still sums to 6",
                rows_a[-2][0] == "vaardigheid domein A" and rows_a[-2][col] == "1" and rows_a[-1][col] == "0"
                and sum(int(x[col]) for x in rows_a[1:]) == 6)

    before = (bank / "links" / f"{E}.json").read_bytes()
    ok &= run("bank_add again without --replace (must fail)", f"{s}/bank_add.py", str(r), "--bank", str(bank), expect_fail=True)
    ok &= check("failed add left the bank untouched", (bank / "links" / f"{E}.json").read_bytes() == before)
    ok &= run("bank_add --replace", f"{s}/bank_add.py", str(r), "--bank", str(bank), "--replace")
    ok &= check("replace kept a dated copy", len(list((bank / "links").glob(f"{E}.*.json"))) == 1)
    run_json = load(r / "run.json")
    run_json["criteria_run"] = "other-generate-run"
    (r / "run.json").write_text(json.dumps(run_json), encoding="utf-8")
    ok &= run("bank_add with other criteria run (must fail)", f"{s}/bank_add.py", str(r), "--bank", str(bank), "--replace", expect_fail=True)

    print("\nALL OK" if ok else "\nSOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
