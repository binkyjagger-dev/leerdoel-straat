"""Shared helpers for the labels step (specs/26): the question universe of a run (exam or toets mode), labeller
files, evidence texts and the computed fields `combination` and `bloom`.

Exam mode (R = an /examen run): questions and points from 21_exam_units.json, texts from R/text/, links from
R/24_mappings.json or, when absent (`/examen --label`), from the bank's links/<exam_id>.json.
Toets mode (R = a /toets run, specs/33 §4): questions and points from 33_items/<opgave>.json, texts from
34_student/<opgave>.md plus the opgave's correctievoorschrift, criteria → group from 30_criteria.json, Bloom per
scorepunt from 32_blueprint.json.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "toets"))
from ecommon import ROOT, Units, bloom_rank, criteria_index, load_json, quote_valid, read_text, validate_schema  # noqa: E402,F401
from tcommon import knob_index, load_knobs, merged_catalogue, pattern_index  # noqa: E402,F401

PREFIX = {"exam": "26_labels", "toets": "34_labels"}


def subjects_dir(argv: list[str]) -> Path:
    return Path(argv[argv.index("--subjects") + 1]) if "--subjects" in argv else ROOT / "subjects"


def bank_dir(subject: str, argv: list[str]) -> Path:
    return Path(argv[argv.index("--bank") + 1]) if "--bank" in argv else subjects_dir(argv) / subject / "examenbank"


class Run:
    """The questions a labels step works on, with texts for evidence checks and links for computed fields."""

    def __init__(self, run_dir: Path, mode: str, bank: Path | None = None, subjects: Path | None = None):
        self.run_dir, self.mode = run_dir, mode
        self.run = load_json(run_dir / "run.json")
        self.subject = self.run["subject"]
        self.bank = bank or ROOT / "subjects" / self.subject / "examenbank"
        self.questions: dict[str, dict] = {}
        self.opgaven: list[str] = []
        if mode == "exam":
            self._load_exam()
        else:
            self._load_toets()
        if mode == "toets" and (run_dir / "30_patterns.json").exists():
            self.catalogue = load_json(run_dir / "30_patterns.json")
        else:
            self.catalogue = merged_catalogue(self.subject, subjects=subjects)
        self.pidx = pattern_index(self.catalogue)
        kp = run_dir / "30_knobs.json"
        self.knobs = knob_index(load_json(kp) if mode == "toets" and kp.exists() else load_knobs())

    # -- exam -------------------------------------------------------------------------------------------------
    def _load_exam(self) -> None:
        u = self.units = Units(self.run_dir)
        for og in u.opgaven:
            self.opgaven.append(og["unit_id"])
            qs = sorted((q for q in u.questions if q["opgave_id"] == og["unit_id"]), key=lambda q: q["number"])
            for i, q in enumerate(qs):
                texts = [u.question_text(q["unit_id"]), read_text(self.run_dir, og.get("text_ref")),
                         read_text(self.run_dir, q.get("cv_ref"))]
                texts += [read_text(self.run_dir, f"text/{q['exam_id']}-bron{n}.txt") for n in q.get("sources", [])]
                self.questions[q["unit_id"]] = {
                    "question_id": q["unit_id"], "question_number": q["number"], "opgave_id": og["unit_id"],
                    "exam_id": q["exam_id"], "points": q["points"], "first_of_opgave": i == 0,
                    "opgave_numbers": [x["number"] for x in qs], "texts": [t for t in texts if t],
                    "tolerant": u.tolerant(q["exam_id"])}
        self._links = None

    def exam_links(self) -> dict[str, list[dict]]:
        """question_id → [{points, group_id, bloom}] from R/24_mappings.json, else the bank's links files."""
        if self._links is None:
            out: dict[str, list[dict]] = {}
            mp = self.run_dir / "24_mappings.json"
            if mp.exists():
                recs = load_json(mp)["links"]
            else:
                recs = []
                for eid in self.units.exams:
                    lp = self.bank / "links" / f"{eid}.json"
                    if lp.exists():
                        recs += load_json(lp)["scorepunten"]
            for r in recs:
                out.setdefault(r["question_id"], []).append(
                    {"points": r["points"], "group_id": r.get("group_id"), "bloom": r.get("bloom")})
            self._links = out
        return self._links

    # -- toets ------------------------------------------------------------------------------------------------
    def _load_toets(self) -> None:
        crit = criteria_index(load_json(self.run_dir / "30_criteria.json")) if (self.run_dir / "30_criteria.json").exists() else {}
        bp = load_json(self.run_dir / "32_blueprint.json") if (self.run_dir / "32_blueprint.json").exists() else {"opgaven": []}
        bp_bloom = {(v["vraag_id"], s["seq"]): s["bloom"] for o in bp["opgaven"] for v in o["vragen"] for s in v["scorepunten"]}
        self._toets_links: dict[str, list[dict]] = {}
        for f in sorted(glob.glob(str(self.run_dir / "33_items" / "*.json"))):
            if ".round" in Path(f).name:
                continue
            it = load_json(f)
            oid = it["opgave_id"]
            self.opgaven.append(oid)
            student = read_text(self.run_dir, f"34_student/{oid}.md")
            cv_text = "\n".join(
                "\n".join([v["cv"]["model_answer"], *[s["text"] for s in v["cv"]["scorepunten"]], *v["cv"]["rules"],
                           *v["cv"]["alternatives"], v["cv"].get("follow_through") or ""]) for v in it["vragen"])
            vs = sorted(it["vragen"], key=lambda v: v["number"])
            for i, v in enumerate(vs):
                self.questions[v["vraag_id"]] = {
                    "question_id": v["vraag_id"], "question_number": v["number"], "opgave_id": oid, "exam_id": None,
                    "points": v["points"], "first_of_opgave": i == 0, "opgave_numbers": [x["number"] for x in vs],
                    "texts": [t for t in (student, cv_text) if t], "tolerant": False}
                self._toets_links[v["vraag_id"]] = [
                    {"points": s["points"], "group_id": (crit.get(s["criterion_id"]) or {}).get("group_id"),
                     "bloom": bp_bloom.get((v["vraag_id"], s["seq"]))} for s in v["cv"]["scorepunten"]]

    # -- shared -----------------------------------------------------------------------------------------------
    def links_of(self, qid: str) -> list[dict]:
        return self.exam_links().get(qid, []) if self.mode == "exam" else self._toets_links.get(qid, [])

    def questions_of(self, opgave_id: str) -> list[dict]:
        return sorted((q for q in self.questions.values() if q["opgave_id"] == opgave_id), key=lambda q: q["question_number"])

    def labeller_files(self, letter: str) -> list[str]:
        return sorted(glob.glob(str(self.run_dir / f"{PREFIX[self.mode]}.{letter}" / "*.json")))

    def evidence_ok(self, qid: str, quote: str) -> bool:
        q = self.questions[qid]
        return any(quote_valid(quote, t, q["tolerant"]) for t in q["texts"])


def computed_fields(links: list[dict]) -> dict:
    """specs/26 §2: combination = distinct group_ids over the linked scorepunten; bloom = max over scorepunten."""
    groups = {l["group_id"] for l in links if l.get("group_id")}
    blooms = [l["bloom"] for l in links if l.get("bloom")]
    return {"combination": len(groups),
            "bloom": max(blooms, key=bloom_rank) if blooms else None,
            "scorepunt_bloom": [{"points": l["points"], "bloom": l.get("bloom"), "group_id": l.get("group_id")} for l in links]}


def load_labeller(run: Run, letter: str) -> tuple[dict[str, dict], list[str]]:
    """question_id → item for one labeller letter; plus schema errors."""
    items, errs = {}, []
    for f in run.labeller_files(letter):
        d = load_json(f)
        e = validate_schema(d, "item_labels.schema.json")
        if e:
            errs.append(f"{Path(f).parent.name}/{Path(f).name}: {e[0]}")
            continue
        if d["labeller"] != letter or d["mode"] != run.mode:
            errs.append(f"{Path(f).parent.name}/{Path(f).name}: labeller/mode {d['labeller']}/{d['mode']} != {letter}/{run.mode}")
        for it in d["items"]:
            items[it["question_id"]] = {**it, "_opgave": d["opgave_id"], "_file": f"{Path(f).parent.name}/{Path(f).name}"}
    return items, errs
