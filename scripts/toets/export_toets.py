#!/usr/bin/env python3
"""T6 — export the toets (specs/35 §1–§2): student version, correctievoorschrift, verantwoording (Word + Markdown),
final bouwplan, twijfellijst, figures and toets.json.

Usage: export_toets.py <run_dir> [--subjects <dir>] [--pdf]

Reads run.json, 31_order.json, 32_blueprint.json, 33_items/, 33_checks/, 34_labels.json, 34_realized.json,
34_solver_compare.json, 35_verification.json (+ .round<N>), 30_criteria.json, 30_patterns.json, 30_knobs.json,
30_reference_profile.json and figures/. Writes to output/:
  <slug>-leerling.md/.docx            cover, opgaven with vragen, informatiebronnen, uitwerkbijlage (page breaks)
  <slug>-correctievoorschrift.md/.docx per vraag maximumscore, model answer, scorepunten, rules, alternatives,
                                      follow-through; figures with answer lines
  <slug>-verantwoording.md/.docx      §2: opdracht · matrijs · Bloom-mix · knoppen (gepland · bouwplan · gerealiseerd ·
                                      centraal examen) · per vraag · patronen · controle
  bouwplan.md (final, blueprint_report.py) · twijfellijst.md · figuren/*.png · toets.json (the toetsbank record)
Every number comes from 31_order.json, 32_blueprint.json, 34_realized.json and 30_reference_profile.json; the script
computes nothing an agent wrote in prose. The Markdown is the source; the docx renders the same blocks. With --pdf
(and LibreOffice on the PATH) every docx is converted to PDF in a temp dir and must have at least one page.
"""
from __future__ import annotations

import datetime
import glob
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from docmodel import write
from tcommon import LABEL_KNOBS, MIX_LEVELS, Report, exam_label, load_json, pattern_codes, save_json
from toetsrun import ToetsRun, subjects_opt

LEVEL_NL = {"4vwo": "4 VWO", "5vwo": "5 VWO", "6vwo": "6 VWO"}


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "toets"


def pct(x) -> str:
    return "–" if x is None else f"{x * 100:.0f} %"


def num(x: float) -> str:
    return (f"{x:.1f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))).replace(".", ",")


def pts(p, s) -> str:
    return f"{num(p)} p · {pct(s)}"


class Toets:
    def __init__(self, R: Path, subjects: Path | None):
        self.R, self.run = R, ToetsRun(R, subjects)
        self.order, self.bp = self.run.order, self.run.blueprint()
        self.items = self.run.items()
        self.realized = load_json(R / "34_realized.json")
        self.labels = {l["question_id"]: l for l in load_json(R / "34_labels.json")["labels"]} if (R / "34_labels.json").exists() else {}
        vp = R / "35_verification.json"
        self.ver = load_json(vp) if vp.exists() else {"vragen": [], "toets_findings": [], "proposed_decisions": []}
        self.ref = self.run.reference or {"pooled": {}, "exams": [], "unknown_knobs": [], "label": "referentie: geen"}
        self.opgaven = self.bp["opgaven"]
        self.onum = {o["opgave_id"]: i + 1 for i, o in enumerate(self.opgaven)}
        self.title = self.order.get("title") or "Toets"
        self.slug = slugify(self.title)
        self.max_score = sum(v["points"] for it in self.items.values() for v in it["vragen"])
        self.open = defaultdict(list)
        for v in self.ver["vragen"]:
            if v["verdict"] == "repair":
                self.open[v["vraag_id"]] += [f for f in v["findings"] if f["severity"] == "must"]

    def vragen(self):
        for o in self.opgaven:
            it = self.items.get(o["opgave_id"])
            if not it:
                continue
            for v in sorted(it["vragen"], key=lambda x: x["number"]):
                yield o, it, v

    def figure_blocks(self, it: dict, fid: str, cv: bool) -> list[tuple]:
        f = next((x for x in it["figures"] if x["figure_id"] == fid), None)
        if f and f["spec"].get("type") == "game_matrix" and f["spec"].get("table"):
            return [("table", f["spec"]["table"], True)]
        png = self.R / "figures" / f"{fid}{'-cv' if cv else ''}.png"
        return [("img", png, f["spec"].get("title", "") if f else "")]

    def source_blocks(self, it: dict, s: dict) -> list[tuple]:
        b = [("h3", f"Informatiebron {s['n']} {s['title']}")]
        if s.get("text"):
            b.append(("p", s["text"]))
        if s.get("table"):
            b.append(("table", s["table"], True))
        if s.get("figure_id"):
            b += self.figure_blocks(it, s["figure_id"], False)
        return b

    # ---------------------------------------------------------------- student version
    def leerling(self) -> list[tuple]:
        o = self.order
        n = sum(1 for _ in self.vragen())
        B = [("h1", self.title),
             ("p", f"**{LEVEL_NL.get(o.get('level'), o.get('level') or '')}** · "
                   + (f"tijd {o['duration_minutes']} minuten · " if o.get("duration_minutes") else "")
                   + f"{n} vragen · maximaal {self.max_score} punten"),
             ("p", "Bij elke vraag staat hoeveel punten je ermee kunt behalen. Gebruik bij de opgaven de informatiebronnen "
                   "achteraan. Vragen met een schema of figuur werk je uit op de uitwerkbijlage."),
             ("pagebreak",)]
        for og in self.opgaven:
            it = self.items.get(og["opgave_id"])
            if not it:
                continue
            B += [("h2", f"Opgave {self.onum[og['opgave_id']]} {it['title']}"), ("p", it["intro"])]
            for v in sorted(it["vragen"], key=lambda x: x["number"]):
                B.append(("p", f"{v['points']}p **{v['number']}** {v['stem']}"))
        if any(it["sources"] for it in self.items.values()):
            B += [("pagebreak",), ("h2", "Informatiebronnen")]
            for og in self.opgaven:
                it = self.items.get(og["opgave_id"])
                if it and it["sources"]:
                    B.append(("p", f"**Opgave {self.onum[og['opgave_id']]} {it['title']}**"))
                    for s in sorted(it["sources"], key=lambda x: x["n"]):
                        B += self.source_blocks(it, s)
        ub = [(it, v) for _, it, v in self.vragen() if v.get("uitwerkbijlage")]
        if ub:
            B += [("pagebreak",), ("h2", "Uitwerkbijlage")]
            for it, v in ub:
                u = v["uitwerkbijlage"]
                B.append(("h3", f"Bij vraag {v['number']}"))
                if u.get("rows"):
                    B.append(("table", u["rows"], True))
                if u.get("figure_id"):
                    B += self.figure_blocks(it, u["figure_id"], False)
                if u.get("text"):
                    B.append(("p", u["text"]))
        return B

    # ---------------------------------------------------------------- correctievoorschrift
    def cv(self) -> list[tuple]:
        B = [("h1", f"Correctievoorschrift — {self.title}"),
             ("p", f"Maximumscore {self.max_score}. Per vraag: het maximum, een voorbeeld van een juist antwoord en de "
                   "scorepunten.")]
        for og in self.opgaven:
            it = self.items.get(og["opgave_id"])
            if not it:
                continue
            B.append(("h2", f"Opgave {self.onum[og['opgave_id']]} {it['title']}"))
            for v in sorted(it["vragen"], key=lambda x: x["number"]):
                cv = v["cv"]
                B += [("h3", f"Vraag {v['number']}"), ("p", f"**maximumscore {cv['maximumscore']}**"),
                      ("p", ("Een voorbeeld van een juiste berekening is:" if cv["calc"] else "Een voorbeeld van een juist antwoord is:")),
                      ("p", cv["model_answer"]),
                      ("bullets", [f"{s['text']} — {s['points']}" for s in cv["scorepunten"]])]
                for r in cv["rules"]:
                    B.append(("p", f"*{r}*"))
                if cv["alternatives"]:
                    B += [("p", "Ook goed:"), ("bullets", cv["alternatives"])]
                if cv.get("follow_through"):
                    B.append(("p", cv["follow_through"]))
            for f in it["figures"]:
                if f.get("answer_spec"):
                    B += [("p", f"**Figuur {f['figure_id']} met antwoord**")] + self.figure_blocks(it, f["figure_id"], True)
        return B

    # ---------------------------------------------------------------- verantwoording
    def ref_cell(self, knob: str, value: str) -> str:
        if knob in (self.ref.get("unknown_knobs") or []) or knob not in (self.ref.get("pooled") or {}):
            return "onbekend"
        main = pct((self.ref["pooled"][knob].get(value) or {}).get("share", 0))
        spread = []
        for e in self.ref.get("exams", []):
            vals = e["knobs"].get(knob) or {}
            tot = sum(vals.values())
            if tot:
                spread.append(f"{exam_label(e['exam_id'])} {pct(vals.get(value, 0) / tot)}")
        return main + (f" ({', '.join(spread)})" if len(spread) > 1 else "")

    def accepted(self, field: str) -> dict | None:
        return next((a for a in self.bp.get("accepted_deviations") or [] if a["field"].split(".")[-1] == field), None)

    def mark(self, outside: bool, field: str) -> str:
        if not outside:
            return ""
        a = self.accepted(field)
        return f" **buiten tolerantie** (geaccepteerd bij pauze 2: {a.get('note') or a['field']})" if a else " **buiten tolerantie** (na herstel)"

    def verantwoording(self) -> list[tuple]:
        o, rz, names = self.order, self.realized, {c: p for c, p in self.run.pidx.items()}
        B = [("h1", f"Verantwoording — {self.title}"),
             ("p", f"{self.run.subject} · {LEVEL_NL.get(o.get('level'), o.get('level') or '')} · {len(self.opgaven)} opgaven · "
                   f"{sum(1 for _ in self.vragen())} vragen · {self.max_score} punten · {self.ref.get('label') or 'referentie: geen'}")]
        # 1 Opdracht
        B += [("h2", "1. Opdracht"), ("p", f"Referentie: {self.ref.get('label') or 'geen'}."),
              ("table", [["leerdoel", "punten"]] + [[m["group_id"], m["points"]] for m in o.get("matrix", [])], True)]
        bm = o.get("bloom_mix")
        B.append(("p", "Bloom-mix: " + (", ".join(f"{k} {pct(v)}" for k, v in bm.items()) if bm else "geen (planner kiest)") + "."))
        B.append(("bullets", [f"{self.run.knobs[k]['label']}: " + ("vrij" if v == "vrij" else ", ".join(f"{x} {pct(s)}" for x, s in v.items()))
                              for k, v in (o.get("knobs") or {}).items() if k in self.run.knobs]))
        # 2 Matrijs
        crit_pts, crit_vr = defaultdict(int), defaultdict(list)
        for _, it, v in self.vragen():
            for s in v["cv"]["scorepunten"]:
                crit_pts[s["criterion_id"]] += s["points"]
                if v["number"] not in crit_vr[s["criterion_id"]]:
                    crit_vr[s["criterion_id"]].append(v["number"])
        B += [("h2", "2. Matrijs"),
              ("table", [["leerdoel", "gepland", "gerealiseerd", ""]] +
               [[m["group_id"], m["ordered"], m["realised"], "gelijk" if m["ok"] else "**afwijking**"] for m in rz["matrix"]], True)]
        excl = set(o.get("criteria_exclude") or [])
        for m in rz["matrix"]:
            g = self.run.groups.get(m["group_id"])
            if not g:
                continue
            rows = [["criterium", "Bloom", "punten", "vragen"]]
            untested = []
            for c in g["criteria"]:
                cid = c["criterion_id"]
                if cid in crit_pts:
                    rows.append([cid, c["bloom"], crit_pts[cid], ", ".join(map(str, crit_vr[cid]))])
                else:
                    untested.append(cid + (" (uitgesloten)" if cid in excl else ""))
            B += [("p", f"**{m['group_id']}** {g['goal'].get('text_student') or ''}"), ("table", rows, True),
                  ("p", "Niet getoetst: " + (", ".join(untested) or "–") + ".")]
        # 3 Bloom
        refb = (self.ref.get("pooled") or {}).get("bloom") or {}
        rows = [["niveau", "gepland (opdracht)", "bouwplan", "gerealiseerd", "centraal examen"]]
        for lv, d in rz["bloom"].items():
            rows.append([lv, pct(d["ordered"]) if bm else "geen mix", pts(d["planned_points"], d["planned"]),
                         pts(d["realised_points"], d["realised"]) + self.mark(d["outside"], "scorepunten"),
                         pct((refb.get(lv) or {}).get("share", 0)) if refb else "onbekend"])
        B += [("h2", "3. Bloom-mix"), ("p", "Per punt; tolerantie ±5 procentpunt, één scorepunt speling."), ("table", rows, True)]
        # 4 Knoppen
        B += [("h2", "4. Knoppen"), ("p", "Per punt, alleen over de vragen waar de knop telt; tolerantie ±10 procentpunt, één vraag "
                                         "speling. Gerealiseerd = gelabeld door twee blinde beoordelaars.")]
        for k in ["pattern"] + LABEL_KNOBS:
            kd = rz["knobs"].get(k)
            if not kd:
                continue
            B.append(("h3", self.run.knobs[k]["label"] + (" — vrij" if kd["ordered"] == "vrij" else "")))
            rows = [["waarde", "gepland (opdracht)", "bouwplan", "gerealiseerd (gelabeld)", "centraal examen"]]
            for v, d in kd["values"].items():
                label = f"{v} {names[v]['name']}" if k == "pattern" and v in names else v
                rows.append([label, "vrij" if d["ordered"] is None else pct(d["ordered"]), pts(d["planned_points"], d["planned"]),
                             pts(d["realised_points"], d["realised"]) + self.mark(d["outside"], k), self.ref_cell(k, v)])
            B.append(("table", rows, True))
        # 5 Per vraag
        rows = [["vraag", "p", "patroon gepland → gelabeld", "criteria (Bloom)", "knoppen gepland → gerealiseerd", "context", "open bevindingen"]]
        pv = {p["vraag_id"]: p for p in rz["per_vraag"]}
        for og, it, v in self.vragen():
            p = pv.get(v["vraag_id"], {})
            diffs = [f"{k}: {p['knobs_plan'].get(k)} → {p['knobs_label'].get(k) if p['knobs_label'].get(k) is not None else 'geschil'}"
                     for k in LABEL_KNOBS if p and p["knobs_plan"].get(k) != p["knobs_label"].get(k)]
            crit = "; ".join(f"{s['criterion_id']} ({b})" for s, b in zip(v["cv"]["scorepunten"], p.get("bloom") or [None] * 99))
            rows.append([v["number"], v["points"], f"{p.get('pattern_plan')} → {p.get('pattern_label') or 'geschil'}", crit,
                         "; ".join(diffs) or "zoals gepland", it["title"],
                         ", ".join(f["id"] for f in self.open.get(v["vraag_id"], [])) or "–"])
        B += [("h2", "5. Per vraag"), ("table", rows, True)]
        # 6 Patronen
        refp = (self.ref.get("pooled") or {}).get("pattern") or {}
        pat = rz["knobs"].get("pattern", {}).get("values", {})
        rows = [["patroon", "punten toets", "%", "centraal examen"]]
        nie = 0.0
        for v, d in pat.items():
            p = names.get(v, {})
            if p and not p.get("in_central_exam", True):
                nie += d["realised_points"]
            rows.append([f"{v} {p.get('name', '')}" + ("" if p.get("in_central_exam", True) else " (niet-examenpatroon)"),
                         num(d["realised_points"]), pct(d["realised"]),
                         pct((refp.get(v) or {}).get("share", 0)) if refp else "onbekend"])
        B += [("h2", "6. Patronen"), ("table", rows, True), ("p", f"Niet-examenpatroon: {num(nie)} punten.")]
        # 7 Controle
        rows = [["opgave", "items", "rekenen", "figuren", "overlap"]]
        for og in self.opgaven:
            oid = og["opgave_id"]
            cells = [oid]
            for suffix in ("", ".calc", ".figures", ".overlap"):
                f = self.R / "33_checks" / f"{oid}{suffix}.json"
                if suffix == ".calc":
                    cells.append("nagerekend" if f.exists() else "–")
                    continue
                if not f.exists():
                    cells.append("–")
                    continue
                d = load_json(f)
                nf = sum(1 for i in d["items"] if i["severity"] == "fail")
                cells.append("geslaagd" if nf == 0 else f"{nf} fout(en)")
            rows.append(cells)
        sc = load_json(self.R / "34_solver_compare.json").get("summary", {}) if (self.R / "34_solver_compare.json").exists() else {}
        rounds = len(glob.glob(str(self.R / "35_verification.round*.json"))) or (1 if self.ver["vragen"] else 0)
        B += [("h2", "7. Controle"), ("table", rows, True),
              ("bullets", [f"Blinde oplosser: {', '.join(f'{k} {v}' for k, v in sc.items()) or '–'}",
                           f"Verifier: {rounds} ronde(n); open bevindingen: {sum(len(x) for x in self.open.values())}",
                           f"Twijfellijst: {self.n_twijfel} punt(en) (twijfellijst.md)"])]
        acc = self.bp.get("accepted_deviations") or []
        if acc:
            B += [("h3", "Geaccepteerde afwijkingen (pauze 2)"),
                  ("bullets", [f"{a['target']} {a['field']} = {a['value']}: {a.get('note') or ''}" for a in acc])]
        return B

    # ---------------------------------------------------------------- twijfellijst
    def twijfel(self) -> list[str]:
        L = []
        for vid, fs in self.open.items():
            for f in fs:
                L.append(f"| {vid} | {f['id']} (must) | {f['evidence']} | {f['fix_hint']} |")
        for v in self.ver["vragen"]:
            for f in v["findings"]:
                if f["severity"] == "should":
                    L.append(f"| {v['vraag_id']} | {f['id']} (should) | {f['evidence']} | {f['fix_hint']} |")
        for f in self.ver.get("toets_findings", []):
            L.append(f"| toets | {f['id']} ({f['severity']}) | {f['evidence']} | {f['fix_hint']} |")
        for f in sorted(glob.glob(str(self.R / "33_checks" / "*.json"))):
            if f.endswith(".calc.json"):
                continue
            for i in load_json(f).get("items", []):
                if i["severity"] == "warn" and i["rule"] in ("IT7", "O6"):
                    L.append(f"| {Path(f).stem} | {i['rule']} (waarschuwing) | {i['message']} | |")
        oc = self.R / "31_order.check.json"
        if oc.exists():
            for i in load_json(oc).get("items", []):
                if i["severity"] == "warn" and i["rule"] == "O6":
                    L.append(f"| opdracht | O6 (waarschuwing) | {i['message']} | |")
        sc = self.R / "34_solver_compare.json"
        if sc.exists():
            for og in load_json(sc)["opgaven"]:
                for e in og.get("exam_example_errors", []):
                    L.append(f"| {og['opgave_id']} | fout in examenvoorbeeld | {e} | melden aan de docent |")
        return L


def pdf_pages(docx: Path) -> int | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", td, str(docx)], capture_output=True, timeout=180)
        pdf = Path(td) / (docx.stem + ".pdf")
        if not pdf.exists():
            return 0
        import pymupdf
        return len(pymupdf.open(str(pdf)))


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    R = Path(argv[1])
    rep = Report("export_toets")
    for f in ("31_order.json", "32_blueprint.json", "34_realized.json"):
        if not (R / f).exists():
            rep.fail("EX", f"missing {f}")
    if rep.failed:
        rep.print_and_exit()
    T = Toets(R, subjects_opt(argv))
    rv = R / "32_blueprint_review.json"
    if not rv.exists() or not load_json(rv).get("approved"):
        rep.warn("EX", "the blueprint has no recorded approval (32_blueprint_review.json approved: true)")
    out = R / "output"
    tw = T.twijfel()
    T.n_twijfel = len(tw)
    files = [write(T.leerling(), out / f"{T.slug}-leerling.md"),
             write(T.cv(), out / f"{T.slug}-correctievoorschrift.md"),
             write(T.verantwoording(), out / f"{T.slug}-verantwoording.md")]
    (out / "twijfellijst.md").write_text("\n".join(
        [f"# Twijfellijst — {T.title}", "",
         "Bevindingen die na de herstelrondes openstaan, waarschuwingen en fouten in examenvoorbeelden. Niets is weggelaten.", "",
         "| waar | wat | bewijs / melding | hint |", "|---|---|---|---|"] + (tw or ["| – | geen | | |"])) + "\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(Path(__file__).parent / "blueprint_report.py"), str(R)] +
                       (["--subjects", str(T.run.subjects)] if "--subjects" in argv else []), capture_output=True, text=True)
    if r.returncode != 0:
        rep.warn("EX", f"bouwplan.md not refreshed: {r.stderr.strip()[:200]}")
    (out / "figuren").mkdir(parents=True, exist_ok=True)
    nfig = 0
    for f in sorted((R / "figures").glob("*.png")) if (R / "figures").exists() else []:
        shutil.copy2(f, out / "figuren" / f.name)
        nfig += 1
    toets_id = T.run.run.get("toets_id") or T.run.run["run_id"]
    record = {"toets_id": toets_id, "subject": T.run.subject, "criteria_run": T.run.run["criteria_run"], "title": T.title,
              "level": T.order.get("level"), "run_id": T.run.run["run_id"],
              "created_at": T.run.run.get("finished_at", datetime.date.today().isoformat())[:10],
              "max_score": T.max_score, "reference": T.order.get("reference"),
              "opgaven": [], "realised": {k: T.realized[k] for k in ("matrix", "bloom", "outside_tolerance")},
              "findings_left": [{"vraag_id": vid, **f} for vid, fs in T.open.items() for f in fs]}
    bpv = {v["vraag_id"]: v for o in T.opgaven for v in o["vragen"]}
    for og in T.opgaven:
        it = T.items.get(og["opgave_id"])
        if not it:
            rep.fail("EX", f"{og['opgave_id']}: no items")
            continue
        vr = []
        for v in sorted(it["vragen"], key=lambda x: x["number"]):
            b = bpv[v["vraag_id"]]
            bl = {s["seq"]: s["bloom"] for s in b["scorepunten"]}
            vr.append({**v, "pattern": b["pattern"], "knobs": b["knobs"], "label": T.labels.get(v["vraag_id"]),
                       "scorepunten": [{"seq": s["seq"], "points": s["points"], "criterion_id": s["criterion_id"],
                                        "group_id": (T.run.crit.get(s["criterion_id"]) or {}).get("group_id"), "bloom": bl.get(s["seq"])}
                                       for s in v["cv"]["scorepunten"]],
                       "open_findings": [f["id"] for f in T.open.get(v["vraag_id"], [])]})
        record["opgaven"].append({"opgave_id": og["opgave_id"], "title": it["title"], "context": og["context"],
                                  "context_tags": og["context_tags"], "reused_from": og.get("reused_from"), "intro": it["intro"],
                                  "data": it["data"], "sources": it["sources"], "figures": it["figures"], "vragen": vr})
    from tcommon import validate_def
    for e in validate_def(record, "toetsbank.schema.json", "toets_file")[:5]:
        rep.fail("EX", f"toets.json: {e}")
    save_json(out / "toets.json", record)
    for md, dx in files:
        rep.info("EX", f"{md.name} + {dx.name}")
        if "--pdf" in argv:
            n = pdf_pages(dx)
            if n is None:
                rep.info("EX", "LibreOffice not found: PDF check skipped")
                break
            (rep.info if n > 0 else rep.fail)("EX", f"{dx.name}: PDF with {n} page(s)")
    rep.info("EX", f"bouwplan.md, twijfellijst.md ({len(tw)} items), {nfig} figures, toets.json ({toets_id})")
    rep.print_and_exit()


if __name__ == "__main__":
    main(sys.argv)
