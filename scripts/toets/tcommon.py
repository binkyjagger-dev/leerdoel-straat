"""Shared helpers for the toets-straat scripts (specs/30–35) and the /examen labels step (specs/26).

Knob definitions (data/toets/knobs.json), the merged pattern catalogue (base + subject layer), knob
applicability and the share arithmetic used by the order checks, the profile and later the blueprint checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
from common import BLOOM_ORDER, DATA, ROOT, Report, bloom_rank, load_json, save_json, validate_schema  # noqa: E402,F401

KNOBS_PATH = DATA / "toets" / "knobs.json"
BASE_PATTERNS_PATH = DATA / "toets" / "patterns_base.json"
SHARE_EPS = 0.001
# knobs the labeller sets per question (specs/26 §2); combination and bloom are computed
LABEL_KNOBS = ["solo", "route", "steps", "sources", "noise", "claim", "new_concept", "schema", "builds_on"]
LABEL_FIELDS = ["pattern"] + LABEL_KNOBS
EXAMPLE_QUALITY = ["ongeschikt", "bruikbaar", "goed"]  # low → high
MIX_LEVELS = [b for b in BLOOM_ORDER if b != "creëren"]  # creëren has no pattern (specs/31 §3)


def validate_def(data, schema_name: str, definition: str) -> list[str]:
    """Validate against #/$defs/<definition> of a schema file."""
    import jsonschema
    schema = load_json(ROOT / "schemas" / schema_name)
    sub = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{definition}"}
    v = jsonschema.Draft202012Validator(sub)
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(v.iter_errors(data), key=lambda e: list(e.absolute_path))]


def clean_reference(ref: dict | None, knobs: dict[str, dict]) -> dict | None:
    """A reference profile whose knob values are no longer valid (e.g. labelled before `sources` changed on
    2026-11-14) must not be shown as a reference: such knobs move to unknown_knobs and are listed in stale_knobs."""
    if not ref or not ref.get("pooled"):
        return ref
    stale = []
    for k, vals in (ref.get("pooled") or {}).items():
        kd = knobs.get(k)
        if kd and isinstance(kd["values"], list) and set(vals) - set(kd["values"]):
            stale.append(k)
    for k in knobs:
        if knobs[k]["settable"] and k != "pattern" and k not in (ref.get("pooled") or {}) and k not in ref.get("unknown_knobs", []):
            stale.append(k)  # knob added after the profile was built (e.g. noise)
    if not stale:
        return ref
    out = dict(ref)
    out["unknown_knobs"] = sorted(set(ref.get("unknown_knobs", [])) | set(stale))
    out["stale_knobs"] = sorted(set(stale))
    return out


def subject_patterns_path(subject: str, subjects: Path | None = None) -> Path:
    return (subjects or ROOT / "subjects") / subject / "toets" / "patterns.json"


def load_knobs(path: Path | None = None) -> dict:
    return load_json(path or KNOBS_PATH)


def knob_index(knobs_doc: dict) -> dict[str, dict]:
    return {k["id"]: k for k in knobs_doc["knobs"]}


def merged_catalogue(subject: str, base_path: Path | None = None, subjects: Path | None = None) -> dict:
    """Base layer + the subject layer (when the subject has one), as one catalogue (#/$defs/merged)."""
    base = load_json(base_path or BASE_PATTERNS_PATH)
    layers = {base["layer"]: base["version"]}
    patterns = list(base["patterns"])
    sp = subject_patterns_path(subject, subjects)
    if sp.exists():
        s = load_json(sp)
        layers[s["layer"]] = s["version"]
        patterns += s["patterns"]
    return {"subject": subject, "layers": layers, "patterns": patterns}


def pattern_index(catalogue: dict) -> dict[str, dict]:
    return {p["code"]: p for p in catalogue["patterns"]}


def pattern_codes(code: str | None) -> list[str]:
    """'P08+B02' → ['P08', 'B02']; None/'' → []."""
    return [c for c in (code or "").split("+") if c]


def same_pattern(a: str | None, b: str | None) -> bool:
    """A '+'-combination is equal regardless of order."""
    return a is not None and b is not None and sorted(pattern_codes(a)) == sorted(pattern_codes(b))


def kinds_of(code: str | None, pidx: dict[str, dict]) -> set[str]:
    return {pidx[c]["kind"] for c in pattern_codes(code) if c in pidx}


def knob_applies(knob: dict, kinds: set[str], first_of_opgave: bool) -> bool:
    """specs/31 §2/§5: does a knob apply to a question with these pattern kinds?"""
    a = knob["applies_to_kinds"]
    if a == "all":
        return True
    if a == "all_but_first_of_opgave":
        return not first_of_opgave
    return bool(kinds & set(a))


def knob_values(knob: dict, pidx: dict[str, dict] | None = None, active_only: bool = True) -> list[str]:
    if knob["values"] == "catalogue":
        return [c for c, p in (pidx or {}).items() if not active_only or p.get("status") == "active"]
    return list(knob["values"])


def share_sum_ok(shares: dict) -> bool:
    return abs(sum(shares.values()) - 1.0) <= SHARE_EPS


def shares_from_points(points: dict[str, float]) -> dict[str, dict]:
    tot = sum(points.values())
    return {v: {"points": round(p, 3), "share": round(p / tot, 3) if tot else 0.0} for v, p in points.items()}


def exam_label(exam_id: str) -> str:
    """'vwo-2025-tv1' → '2025-I' (Dutch column header)."""
    parts = exam_id.split("-")
    try:
        year, tv = parts[1], int(parts[2][2:])
        return f"{year}-{'I' * tv if tv <= 3 else tv}"
    except (IndexError, ValueError):
        return exam_id
