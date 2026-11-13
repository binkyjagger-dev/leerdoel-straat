"""Loading a /toets run folder (specs/33 §4) for the T2–T5 scripts."""
from __future__ import annotations

import glob
import re
from pathlib import Path

from tcommon import ROOT, knob_index, load_json, load_knobs, merged_catalogue, pattern_index


class ToetsRun:
    def __init__(self, run_dir: Path, subjects: Path | None = None):
        self.R = Path(run_dir)
        self.run = load_json(self.R / "run.json")
        self.subject = self.run["subject"]
        self.subjects = subjects or ROOT / "subjects"
        self.order = load_json(self.R / "31_order.json") if (self.R / "31_order.json").exists() else {}
        self.criteria_doc = load_json(self.R / "30_criteria.json")
        self.groups, self.crit = {}, {}
        for g in self.criteria_doc["groups"]:
            self.groups[g["group_id"]] = g
            for c in g["criteria"]:
                self.crit[c["criterion_id"]] = {**c, "group_id": g["group_id"]}
        cat = load_json(self.R / "30_patterns.json") if (self.R / "30_patterns.json").exists() \
            else merged_catalogue(self.subject, subjects=self.subjects)
        self.pidx = pattern_index(cat)
        self.knobs = knob_index(load_json(self.R / "30_knobs.json") if (self.R / "30_knobs.json").exists() else load_knobs())
        hp = self.R / "30_context_history.json"
        self.history = load_json(hp)["contexts"] if hp.exists() else []
        rp = self.R / "30_reference_profile.json"
        self.reference = load_json(rp) if rp.exists() else None

    def blueprint(self) -> dict:
        return load_json(self.R / "32_blueprint.json")

    def items(self, opgave: str | None = None) -> dict[str, dict]:
        out = {}
        for f in sorted(glob.glob(str(self.R / "33_items" / "*.json"))):
            if ".round" in Path(f).name:
                continue
            d = load_json(f)
            if opgave is None or d["opgave_id"] == opgave:
                out[d["opgave_id"]] = d
        return out

    def conventions_text(self) -> str:
        p = self.subjects / self.subject / "toets" / "conventions.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def allowlist(self) -> list[str]:
        """Bullets under the 'Overlap-allowlist' heading of conventions.md."""
        text, out, on = self.conventions_text(), [], False
        for line in text.splitlines():
            if line.startswith("#"):
                on = "allowlist" in line.lower()
                continue
            if on and line.strip().startswith("- "):
                out.append(line.strip()[2:].strip())
        return out

    def btw_default(self) -> float | None:
        if (self.order.get("conventions") or {}).get("btw") is not None:
            return float(self.order["conventions"]["btw"])
        m = re.search(r"[Bb]tw:?\s*(\d+(?:,\d+)?)\s*%", self.conventions_text())
        return float(m.group(1).replace(",", ".")) / 100 if m else None

    def toetsbank(self) -> Path:
        return self.subjects / self.subject / "toetsbank"


def opt(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None


def subjects_opt(argv: list[str]) -> Path | None:
    return Path(opt(argv, "--subjects")) if opt(argv, "--subjects") else None
