#!/usr/bin/env python3
"""Exercise the toets-straat phase-1 scripts (build steps 1–3) on tests/fixtures/toets. Usage: python tests/run_toets_fixture.py

Step 1: patterns.py (validate the real seeds and the fixture layer, merged, add/retire against decisions).
Step 2: /examen E7 — label_merge.py (exam mode: a disagreement, an invalid quote, a NIEUW proposal, an R round),
        check_labels.py (LB4 caught, LB6 warning), bank_labels_add.py (replace rules), profile_build.py (seed, labels,
        conservation); label_merge.py --toets and check_labels.py --toets on a toets run layout.
Step 3: validate_toets.py order (valid, invalid, draft with ASK lines), form_build.py (HTML parses, embedded JSON
        loads, JS syntax via node when present, a headless-browser self-test when Chrome/Chromium is present).
Step 4: blueprint_check.py (a passing blueprint with --write; one that breaks BP3, BP5, BP7 and BP8),
        blueprint_apply.py (context change, accepted deviation, deviation not accepted, replan), blueprint_report.py.
Everything runs in a temp dir; the repo's subjects/ are only read.
"""
from __future__ import annotations
import html, json, re, shutil, subprocess, sys, tempfile
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
PY = sys.executable
FX = ROOT / "tests" / "fixtures" / "toets"
E1, E2 = "vwo-2030-tv1", "vwo-2031-tv1"


def run(label, *args, expect_fail=False, expect_code=None):
    print(f"== {label}")
    r = subprocess.run([PY, "-X", "utf8", *args], cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
    print(r.stdout, end="")
    if expect_code is not None:
        ok = r.returncode == expect_code
    else:
        ok = (r.returncode != 0) == expect_fail
    if not ok:
        print(r.stderr, end="")
        print(f"!! {'FAILED' if r.returncode else 'UNEXPECTEDLY PASSED'} (exit {r.returncode}): {label}")
    run.last = r.stdout + r.stderr
    return ok


def check(label, cond):
    print(f"   {'ok ' if cond else 'NOK'} {label}")
    return bool(cond)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


class ScriptGrab(HTMLParser):
    def __init__(self):
        super().__init__(); self.cur = None; self.scripts = []
    def handle_starttag(self, tag, attrs):
        if tag == "script": self.cur = [dict(attrs), ""]
    def handle_data(self, data):
        if self.cur is not None: self.cur[1] += data
    def handle_endtag(self, tag):
        if tag == "script" and self.cur is not None: self.scripts.append(self.cur); self.cur = None


def browser():
    for b in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        p = shutil.which(b)
        if p: return p
    return None


def main():
    tmp = Path(tempfile.mkdtemp())
    subj, bank, tb = tmp / "subjects", tmp / "bank", tmp / "toetsbank"
    shutil.copytree(FX / "subjects", subj)
    shutil.copytree(FX / "bank", bank)
    shutil.copytree(FX / "toetsbank", tb)
    shutil.copy(FX / "criteria.json", bank / "criteria.json")
    shutil.copy(FX / "source_units.json", bank / "source_units.json")
    base = tmp / "patterns_base.json"
    shutil.copy(ROOT / "data" / "toets" / "patterns_base.json", base)
    S = ["--subjects", str(subj)]
    t, ok = "scripts/toets", True

    # ---------------- step 1: catalogue ----------------
    ok &= run("patterns validate (repo seeds)", f"{t}/patterns.py", "validate")
    ok &= run("patterns validate (fixture layer)", f"{t}/patterns.py", "validate", "fixturevak", *S, "--base", str(base))
    ok &= run("patterns merged fixturevak", f"{t}/patterns.py", "merged", "fixturevak", *S, "--base", str(base), "--out", str(tmp / "merged.json"))
    m = load(tmp / "merged.json")
    ok &= check("merged = 13 base + 1 subject pattern, P16 not in central exam",
                len(m["patterns"]) == 14 and next(p for p in m["patterns"] if p["code"] == "P16")["in_central_exam"] is False)
    before = (subj / "fixturevak/toets/patterns.json").read_bytes()
    ok &= run("patterns add against an OPEN decision (must fail)", f"{t}/patterns.py", "add", "fixturevak", "fixturevak-002",
              str(FX / "add/X02.json"), *S, "--base", str(base), expect_fail=True)
    ok &= run("patterns add an invalid record (creëren; must fail)", f"{t}/patterns.py", "add", "fixturevak", "fixturevak-001",
              str(FX / "add/X02_bad.json"), *S, "--base", str(base), expect_fail=True)
    ok &= check("failed adds left the layer untouched", (subj / "fixturevak/toets/patterns.json").read_bytes() == before)
    ok &= run("patterns add X02 against answered fixturevak-001", f"{t}/patterns.py", "add", "fixturevak", "fixturevak-001",
              str(FX / "add/X02.json"), *S, "--base", str(base))
    x02 = next(p for p in load(subj / "fixturevak/toets/patterns.json")["patterns"] if p["code"] == "X02")
    ok &= check("X02 written with source=decision and the decision id", x02["source"] == "decision" and x02["decision"] == "fixturevak-001")
    p07 = dict(next(p for p in load(base)["patterns"] if p["code"] == "P07")); p07["layer"] = "fixturevak"
    (tmp / "p07.json").write_text(json.dumps(p07), encoding="utf-8")
    ok &= run("patterns add a base code to a subject layer (must fail)", f"{t}/patterns.py", "add", "fixturevak", "fixturevak-001",
              str(tmp / "p07.json"), *S, "--base", str(base), expect_fail=True)
    ok &= run("patterns retire X02", f"{t}/patterns.py", "retire", "X02", "fixturevak-001", *S, "--base", str(base))
    x02 = next(p for p in load(subj / "fixturevak/toets/patterns.json")["patterns"] if p["code"] == "X02")
    ok &= check("X02 retired, not deleted", x02["status"] == "retired" and x02["retired_by"] == "fixturevak-001")
    ok &= run("patterns validate after add/retire", f"{t}/patterns.py", "validate", "fixturevak", *S, "--base", str(base))
    sys.path.insert(0, str(ROOT / "scripts"))
    from common import validate_schema  # noqa: E402
    ok &= check("seed_profile.json (economie) validates against reference_profile",
                not validate_schema(load(ROOT / "subjects/economie/toets/seed_profile.json"), "reference_profile.schema.json"))
    ok &= check("knobs.json validates against knobs", not validate_schema(load(ROOT / "data/toets/knobs.json"), "knobs.schema.json"))

    # ---------------- step 2: E7 labels (exam mode) ----------------
    e, r = "scripts/exam", tmp / "label_run"
    shutil.copytree(FX / "exam_run", r)
    B = ["--bank", str(bank), *S]
    ok &= run("profile_build before labels (seed)", f"{e}/profile_build.py", "fixturevak", *B)
    prof = load(bank / "profiel/referentieprofiel.json")
    ok &= check("seed profile used, labelled voorlopig", prof["source"] == "seed-analysis-2030-05" and "voorlopig" in prof["label"])
    ok &= run("label_merge (A/B, one disagreement)", f"{e}/label_merge.py", str(r), *B)
    lab = {l["question_id"]: l for l in load(r / "26_labels.json")["labels"]}
    ok &= check("q1 pattern P08 vs P07 → disputed, value null", lab[f"{E1}-q1"]["pattern"] is None and lab[f"{E1}-q1"]["confidence"]["pattern"] == "disputed")
    ok &= check("two-valued knob (q1 route gegeven vs zelf vinden) → disputed, not medium (bouwvraag 1)",
                lab[f"{E1}-q1"]["route"] is None and lab[f"{E1}-q1"]["confidence"]["route"] == "disputed")
    ok &= check("combined pattern in a different order agrees (P08+X01 = X01+P08) → high",
                lab[f"{E2}-q1"]["pattern"] == "P08+X01" and lab[f"{E2}-q1"]["confidence"]["pattern"] == "high")
    ok &= check("q2 solo one step apart → medium, lower value", lab[f"{E1}-q2"]["solo"] == "multistructureel" and lab[f"{E1}-q2"]["confidence"]["solo"] == "medium")
    ok &= check("q3 builds_on ja on question 1; q1 builds_on null (first of opgave)",
                lab[f"{E1}-q3"]["builds_on_questions"] == [1] and lab[f"{E1}-q1"]["builds_on"] is None)
    ok &= check("combination and bloom computed from the bank links (q3: 2 leerdoelen, evalueren)",
                lab[f"{E1}-q3"]["combination"] == 2 and lab[f"{E1}-q3"]["bloom"] == "evalueren")
    ok &= check("points from units, not from labeller B (q1 of 2031: 2, B said 5)", lab[f"{E2}-q1"]["points"] == 2)
    ok &= check("route/schema null where the pattern does not apply (P01)", lab[f"{E1}-q2"]["route"] is None and lab[f"{E1}-q2"]["schema"] is None)
    pp = load(r / "26_proposed_patterns.json")
    ok &= check("NIEUW proposal collected once, as an open catalogue question",
                len(pp["questions"]) == 1 and pp["questions"][0]["applies_to"] == ["catalogue"]
                and not validate_schema(pp, "intake_questions.schema.json"))
    ok &= run("check_labels (invalid quote of B → LB4 fails)", f"{e}/check_labels.py", str(r), *B, expect_fail=True)
    ok &= check("LB4 names labeller B and the field; LB6 warns on B's points",
                "FAIL  LB4  26_labels.B" in run.last and "evidence for solo" in run.last and "WARN  LB6" in run.last)
    shutil.copy(FX / f"exam_fix/26_labels.B/{E1}-o1.json", r / f"26_labels.B/{E1}-o1.json")
    ok &= run("check_labels after the relaunched labeller B", f"{e}/check_labels.py", str(r), *B)
    shutil.copy(r / "26_labels.json", r / "26_labels.round1.json")
    shutil.copytree(FX / "exam_repair/26_labels.R", r / "26_labels.R")
    ok &= run("label_merge with R", f"{e}/label_merge.py", str(r), *B)
    lab = {l["question_id"]: l for l in load(r / "26_labels.json")["labels"]}
    ok &= check("R decides q1: P08, zelf vinden, high, repaired_fields",
                lab[f"{E1}-q1"]["pattern"] == "P08" and lab[f"{E1}-q1"]["route"] == "zelf vinden"
                and lab[f"{E1}-q1"]["confidence"]["pattern"] == "high" and "pattern" in lab[f"{E1}-q1"]["repaired_fields"])
    ok &= run("check_labels with R", f"{e}/check_labels.py", str(r), *B)

    ok &= run("bank_labels_add", f"{e}/bank_labels_add.py", str(r), "--bank", str(bank))
    ok &= check("labels/<exam>.json for both exams", (bank / f"labels/{E1}.json").exists() and (bank / f"labels/{E2}.json").exists())
    before = (bank / f"labels/{E1}.json").read_bytes()
    ok &= run("bank_labels_add again without --replace (must fail)", f"{e}/bank_labels_add.py", str(r), "--bank", str(bank), expect_fail=True)
    ok &= check("failed add left the labels untouched", (bank / f"labels/{E1}.json").read_bytes() == before)
    ok &= run("bank_labels_add --replace", f"{e}/bank_labels_add.py", str(r), "--bank", str(bank), "--replace")
    ok &= check("replace kept a dated copy", len(list((bank / "labels").glob(f"{E1}.*.json"))) == 1)

    ok &= run("profile_build from labels", f"{e}/profile_build.py", "fixturevak", *B)
    prof = load(bank / "profiel/referentieprofiel.json")
    pool = prof["pooled"]
    ok &= check("label 'referentie: 2 examens (2030-I, 2031-I)', 14 points, dated copy ignored",
                prof["label"] == "referentie: 2 examens (2030-I, 2031-I)" and prof["points"] == 14 and prof["n_questions"] == 6)
    ok &= check("pattern shares by points; NIEUW (3 p) left out", abs(sum(v["share"] for v in pool["pattern"].values()) - 1) < 0.01
                and prof["excluded"]["pattern"] == {"nieuw": 3.0})
    ok &= check("combined pattern P08+X01 (2 p) split evenly: P08 3 + 1 = 4, X01 1 (bouwvraag 2)",
                pool["pattern"]["P08"]["points"] == 4 and pool["pattern"]["X01"]["points"] == 1
                and sum(prof["exams"][1]["knobs"]["pattern"].values()) + 3 == 5)
    ok &= check("route only over calculation/schema questions; NIEUW left out of route and schema (bouwvraag 6)",
                pool["route"] == {"gegeven": {"points": 2.0, "share": 0.286}, "zelf vinden": {"points": 5.0, "share": 0.714}}
                and prof["excluded"]["route"] == {"nieuw": 3.0, "not_applicable": 4.0}
                and prof["excluded"]["schema"] == {"nieuw": 3.0, "not_applicable": 9.0})
    ok &= check("builds_on over non-first questions only (7 p first of opgave)", prof["excluded"]["builds_on"] == {"not_applicable": 7.0})
    ok &= check("bloom per scorepunt from links; unlinked point excluded",
                pool["bloom"]["toepassen"]["points"] == 8 and prof["excluded"]["bloom"] == {"unlinked": 1.0})
    ok &= check("per-exam columns kept", [x["exam_id"] for x in prof["exams"]] == [E1, E2] and prof["exams"][0]["knobs"]["combination"] == {"1": 7, "2": 2})
    stats = load(bank / "profiel/patronen_stats.json")["patterns"]
    ok &= check("pattern stats with example candidates (P08: 2030 v1 goed); combined question once per pattern, full points for min/max",
                stats["P08"]["examples"][0]["question_number"] == 1 and stats["P08"]["examples"][0]["example_quality"] == "goed"
                and stats["P08"]["n_questions"] == 2 and stats["P08"]["points"] == {"sum": 4.0, "min": 2, "max": 3})
    md = (bank / "profiel/referentieprofiel.md").read_text(encoding="utf-8")
    ok &= check("referentieprofiel.md in Dutch with exam columns and left-out points",
                "| waarde | eindexamen (alle) | 2030-I | 2031-I |" in md and "Weggelaten: 3 p nieuw patroon." in md
                and "Weggelaten: 3 p nieuw patroon, 4 p niet van toepassing." in md)
    bad = tmp / "bank_bad"; shutil.copytree(bank, bad)
    lf = bad / f"labels/{E1}.json"; lj = load(lf); lj["questions"][0]["points"] = 4
    lf.write_text(json.dumps(lj, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(bad / "profiel")
    ok &= run("profile_build with a tampered points value (conservation; must fail)", f"{e}/profile_build.py", "fixturevak",
              "--bank", str(bad), *S, expect_fail=True)
    ok &= check("conservation failure wrote nothing", not (bad / "profiel").exists())
    ok &= run("profile_build for a subject without labels and seed (empty reference)", f"{e}/profile_build.py", "bedrijfseconomie",
              "--bank", str(tmp / "nobank"))
    ok &= check("empty reference says so", load(tmp / "nobank/profiel/referentieprofiel.json")["source"] == "none")

    # ---------------- step 2: toets mode ----------------
    tr = tmp / "toets_run"
    shutil.copytree(FX / "toets_run", tr)
    shutil.copy(FX / "criteria.json", tr / "30_criteria.json")
    shutil.copy(ROOT / "data/toets/knobs.json", tr / "30_knobs.json")
    ok &= run("patterns merged → 30_patterns.json", f"{t}/patterns.py", "merged", "fixturevak", *S, "--base", str(base), "--out", str(tr / "30_patterns.json"))
    ok &= run("label_merge --toets", f"{e}/label_merge.py", str(tr), "--toets", *S)
    tl = {l["question_id"]: l for l in load(tr / "34_labels.json")["labels"]}
    ok &= check("toets mode: steps 1 vs 2 → medium 1; combination from items + criteria; bloom from the blueprint",
                tl["O1-V1"]["steps"] == "1" and tl["O1-V1"]["confidence"]["steps"] == "medium"
                and tl["O1-V2"]["combination"] == 2 and tl["O1-V2"]["bloom"] == "evalueren" and tl["O1-V1"]["example_quality"] is None)
    ok &= run("check_labels --toets", f"{e}/check_labels.py", str(tr), "--toets", *S)

    # ---------------- step 3: order validation ----------------
    O = ["--bank", str(bank), "--toetsbank", str(tb), *S]
    ok &= run("validate_toets order (valid)", f"{t}/validate_toets.py", "order", str(FX / "orders/order_valid.json"), *O)
    ok &= run("validate_toets order (invalid; must fail)", f"{t}/validate_toets.py", "order", str(FX / "orders/order_invalid.json"), *O, expect_fail=True)
    out = run.last
    ok &= check("invalid order: O2, O3 (sum, value, computed knob, creëren), O4 and O5 all reported",
                all(s in out for s in ("FAIL  O2   matrix group X9.9-01", "X1.2-01-z", "shares sum to 0.900", "value '5' not allowed",
                                       "computed knob", "creëren", "FAIL  O4", "FAIL  O5")))
    ok &= run("validate_toets order --draft (missing knobs are questions)", f"{t}/validate_toets.py", "order",
              str(FX / "orders/order_draft.json"), *O, "--draft", "--ask-out", str(tmp / "ask.json"))
    ask = load(tmp / "ask.json")["ask"]
    ok &= check("draft: 7 knobs + bloom_mix to ask, with central-exam reference shares",
                len(ask) == 8 and ask[0]["field"] == "bloom_mix" and ask[1]["reference"]["multistructureel"] == 0.5)
    ok &= check("draft: O6 warnings (all criteria excluded; route without calculation pattern)",
                run.last.count("WARN  O6") == 2)
    ok &= run("validate_toets order on the draft without --draft (incomplete; must fail)", f"{t}/validate_toets.py", "order",
              str(FX / "orders/order_draft.json"), *O, expect_fail=True)
    ok &= run("validate_toets without a subcommand prints usage (exit 2)", f"{t}/validate_toets.py", "nothing", expect_code=2)

    # ---------------- step 3: form ----------------
    form = tmp / "form.html"
    ok &= run("form_build", f"{t}/form_build.py", "fixturevak", "--bank", str(bank), "--toetsbank", str(tb), *S,
              "--base", str(base), "--out", str(form))
    text = form.read_text(encoding="utf-8")
    g = ScriptGrab(); g.feed(text)
    data = next((json.loads(s) for a, s in g.scripts if a.get("id") == "toets-data"), None)
    ok &= check("form parses; embedded JSON loads (groups, reference, catalogue, knobs, history, reuse, templates)",
                data is not None and len(data["groups"]) == 2 and data["reference"]["code"] == "bank-2-examens"
                and any(p["code"] == "X01" for p in data["catalogue"]) and not any(p["code"] == "X02" for p in data["catalogue"])
                and len(data["contexts"]) == 1 and len(data["reuse"]) == 1 and data["templates"][0]["name"] == "mijn-5vwo")
    ok &= check("no network references in the form", not re.search(r"(src|href)=[\"']https?:", text) and "fetch(" not in text)
    ok &= check("Dutch UI headings present", all(h in text for h in ("Toetsmatrijs", "Bloom-mix", "Knoppen", "Zet op eindexamen", "Download toetsopdracht.json")))
    js = next(s for a, s in g.scripts if not a)
    if shutil.which("node"):
        (tmp / "form.js").write_text(js, encoding="utf-8")
        r2 = subprocess.run(["node", "--check", str(tmp / "form.js")], capture_output=True, text=True)
        ok &= check("form JavaScript passes node --check", r2.returncode == 0)
    else:
        print("   --  node not found: JS syntax check skipped")
    b = browser()
    if b:
        try:
            r3 = subprocess.run([b, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=5000", "--dump-dom",
                                 form.resolve().as_uri() + "#selftest"], capture_output=True, text=True, timeout=90,
                                encoding="utf-8", errors="replace")
            mt = re.search(r'<pre id="selftest">(.*?)</pre>', r3.stdout, re.S)
            st = json.loads(html.unescape(mt.group(1))) if mt and mt.group(1).strip() else None
        except Exception as ex:  # pragma: no cover
            st = None; print(f"   --  browser run failed: {ex}")
        ok &= check("headless browser: page renders 2 matrix rows and 10 knob blocks, self-test order has no problems",
                    st is not None and st["rows"] == 2 and st["knobs"] == 10 and st["problems"] == [])
        if st:
            (tmp / "selftest_order.json").write_text(json.dumps(st["order"], ensure_ascii=False), encoding="utf-8")
            ok &= run("validate_toets order on the order the form built", f"{t}/validate_toets.py", "order", str(tmp / "selftest_order.json"), *O)
    else:
        print("   --  no Chrome/Chromium found: headless form self-test skipped")

    ok &= step4(tmp, subj, bank, S)
    print("\nALL OK" if ok else "\nSOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


def pipeline_run(tmp: Path, subj: Path, bank: Path, S: list[str], name: str) -> Path:
    """A /toets run folder from tests/fixtures/toets/pipeline, with the T0 copies."""
    R = tmp / name
    shutil.copytree(FX / "pipeline", R)
    shutil.copy(FX / "criteria.json", R / "30_criteria.json")
    shutil.copy(ROOT / "data/toets/knobs.json", R / "30_knobs.json")
    shutil.copy(bank / "profiel/referentieprofiel.json", R / "30_reference_profile.json")
    subprocess.run([PY, "-X", "utf8", "scripts/toets/patterns.py", "merged", "fixturevak", *S, "--out", str(R / "30_patterns.json")],
                   cwd=ROOT, capture_output=True)
    return R


def step4(tmp: Path, subj: Path, bank: Path, S: list[str]) -> bool:
    t, ok = "scripts/toets", True
    R = pipeline_run(tmp, subj, bank, S, "toets_t2")
    ok &= run("validate_toets blueprint (schema)", f"{t}/validate_toets.py", "blueprint", str(R))
    ok &= run("blueprint_check (valid) --write", f"{t}/blueprint_check.py", str(R), *S, "--write")
    bp = load(R / "32_blueprint.json")
    ok &= check("planned_shares and coverage written by the script (Bloom toepassen 0.556; X1.2-01-a untested)",
                bp["planned_shares"]["bloom"]["toepassen"] == 0.556
                and next(c for c in bp["coverage"]["per_group"] if c["group_id"] == "X1.2-01")["criteria_not_tested"] == ["X1.2-01-a"])
    ok &= check("check report written", (R / "32_blueprint.check.json").exists())
    ok &= run("blueprint_check (broken blueprint; must fail)", f"{t}/blueprint_check.py", str(R), *S,
              "--file", str(R / "32_blueprint_bad.json"), expect_fail=True)
    out = run.last
    ok &= check("BP3 group points, BP5 Bloom outside pattern and > criterion + 1, BP7 solo and Bloom outside tolerance, BP8 history",
                all(s in out for s in ("FAIL  BP3  group X1.1-01: 6 points", "not in pattern P01", "> criterion X1.1-01-b",
                                       "FAIL  BP7  solo 'relationeel'", "FAIL  BP7  Bloom-mix", "FAIL  BP8  O2: context tags")))
    ok &= run("blueprint_report", f"{t}/blueprint_report.py", str(R), *S)
    md = (R / "output/bouwplan.md").read_text(encoding="utf-8")
    ok &= check("bouwplan.md: opgaven, matrix, Bloom and knobs opdracht vs bouwplan vs centraal examen, coverage",
                "## O1 Schoenmaker Zool" in md and "| leerdoel | opdracht | bouwplan |" in md
                and "| niveau | opdracht | bouwplan | centraal examen |" in md and "X1.2-01-a (onthouden): uitgesloten" in md)
    # teacher review: change not accepted → check fails; accepted → warning; replan → exit 3
    R2 = pipeline_run(tmp, subj, bank, S, "toets_t2_noaccept")
    shutil.copy(R2 / "32_blueprint_review_noaccept.json", R2 / "32_blueprint_review.json")
    ok &= run("blueprint_apply (teacher change without accept)", f"{t}/blueprint_apply.py", str(R2))
    ok &= run("blueprint_check after an unaccepted change (must fail BP7)", f"{t}/blueprint_check.py", str(R2), *S, expect_fail=True)
    ok &= check("BP7 failure names the teacher's change", "FAIL  BP7  solo 'relationeel'" in run.last)
    ok &= run("blueprint_apply (context change + accepted deviation)", f"{t}/blueprint_apply.py", str(R))
    bp = load(R / "32_blueprint.json")
    o2 = next(o for o in bp["opgaven"] if o["opgave_id"] == "O2")
    ok &= check("context replaced and its tags cleared; accepted deviation recorded; previous blueprint kept",
                o2["context"].startswith("bakkerij met een bezorgdienst") and o2["context_tags"] == []
                and bp["accepted_deviations"][0]["field"] == "knobs.solo" and (R / "32_blueprint.round1.json").exists())
    ok &= run("blueprint_check after the accepted deviation (passes, BP7 as warning)", f"{t}/blueprint_check.py", str(R), *S)
    ok &= check("BP7 reported as accepted deviation", "WARN  BP7  solo 'relationeel'" in run.last and "geaccepteerd" in run.last)
    ok &= run("blueprint_report marks the accepted deviation", f"{t}/blueprint_report.py", str(R), *S)
    ok &= check("bouwplan.md lists the accepted deviation",
                "buiten tolerantie (geaccepteerd)" in (R / "output/bouwplan.md").read_text(encoding="utf-8"))
    shutil.copy(R / "32_blueprint_review_replan.json", R / "32_blueprint_review.json")
    before = (R / "32_blueprint.json").read_bytes()
    ok &= run("blueprint_apply replan (exit 3, nothing applied)", f"{t}/blueprint_apply.py", str(R), expect_code=3)
    ok &= check("replan left the blueprint untouched", (R / "32_blueprint.json").read_bytes() == before)
    return ok


if __name__ == "__main__":
    main()
