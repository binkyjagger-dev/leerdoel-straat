"""Shared helpers for the leerdoel-straat validators."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Windows consoles default to cp1252; make every script print UTF-8 safely.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMAS = ROOT / "schemas"

BLOOM_ORDER = ["onthouden", "begrijpen", "toepassen", "analyseren", "evalueren", "creëren"]


def load_json(path: str | Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def bloom_rank(level: str) -> int:
    return BLOOM_ORDER.index(level)


EXAM_VALUES = ["CE", "SE", "CE+SE"]


def exam_for(by_id: dict, unit_id: str) -> str | None:
    """Exam allocation of a unit (specs/01 §2 P4): its own `exam`, else the nearest ancestor's; None if unknown."""
    cur, seen = by_id.get(unit_id), set()
    while cur is not None and cur["unit_id"] not in seen:
        if cur.get("exam"):
            return cur["exam"]
        seen.add(cur["unit_id"])
        cur = by_id.get(cur["parent_id"]) if cur.get("parent_id") else None
    return None


def exam_label(value: str | None) -> str:
    """Dutch report/CSV label for an exam value."""
    return value or ""


# ---------------------------------------------------------------------------
# Key concepts (specs/01 §2 P5, specs/02 §5, specs/04 C3/G8)
# ---------------------------------------------------------------------------

def normalise_term(term: str) -> str:
    """Case/whitespace-insensitive key for a concept; a bracketed abbreviation is dropped."""
    t = re.sub(r"\s*\([^)]*\)", "", term)
    return normalise_ws(t)


def concept_pool(by_id: dict, unit_id: str) -> list[tuple[str, str]]:
    """(concept, carrier_unit_id) for the unit's own `concepts` and those of its ancestors."""
    out, cur, seen = [], by_id.get(unit_id), set()
    while cur is not None and cur["unit_id"] not in seen:
        for c in cur.get("concepts") or []:
            out.append((c, cur["unit_id"]))
        seen.add(cur["unit_id"])
        cur = by_id.get(cur["parent_id"]) if cur.get("parent_id") else None
    return out


def concept_texts(by_id: dict, unit_id: str) -> str:
    """Normalised leaf text + parent subdomein text, the verbatim fallback for G8."""
    u = by_id.get(unit_id)
    parts = [u["text"]] if u else []
    if u and u.get("parent_id") and by_id.get(u["parent_id"]):
        parts.append(by_id[u["parent_id"]]["text"])
    return normalise_ws(" ".join(parts))


def concept_admissible(term: str, by_id: dict, unit_id: str) -> bool:
    key = normalise_term(term)
    if not key:
        return False
    if any(normalise_term(c) == key for c, _ in concept_pool(by_id, unit_id)):
        return True
    return key in concept_texts(by_id, unit_id)


def normalise_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("­", "")).strip().lower()


# ---------------------------------------------------------------------------
# Bloom verb tables: generic (data/bloom_verbs_nl.json) + optional subject
# overlay (subjects/<subject>/bloom_verbs.json). specs/02 §2 rule 6, specs/06 §7.
# ---------------------------------------------------------------------------

SUBJECTS = ROOT / "subjects"
GENERIC_VERBS = DATA / "bloom_verbs_nl.json"


def stem_verb(verb: str) -> str:
    """Strip bracketed qualifiers: 'tekenen (volgens een gegeven model)' -> 'tekenen'."""
    return re.sub(r"\s*\(.*?\)\s*", " ", verb).strip().lower()


def subject_verb_table_path(subject: str | None) -> Path | None:
    if not subject:
        return None
    p = SUBJECTS / subject / "bloom_verbs.json"
    return p if p.exists() else None


def subject_for(path: str | Path) -> str | None:
    """Find the `subject` of the run a file belongs to: nearest run.json up the tree (at most 3 levels)."""
    p = Path(path).resolve()
    d = p if p.is_dir() else p.parent
    for _ in range(3):
        rj = d / "run.json"
        if rj.exists():
            try:
                return load_json(rj).get("subject")
            except Exception:  # pragma: no cover
                return None
        d = d.parent
    return None


def merge_verb_rules(generic: dict, overlay: dict | None, subject: str | None = None,
                     overlay_path: str | Path | None = None) -> dict:
    """Return the effective verb table: generic with the overlay applied per verb.

    - a verb in the overlay is removed from every generic level and from `ambiguous`,
      then placed at its overlay level; two overlay levels -> ambiguous between them;
    - `source_verb_hints` gets the overlay level for those verbs;
    - `forbidden_criterion_verbs_extra` is appended; nothing is ever un-forbidden;
    - `_effective` records subject, paths, decision and the list of overrides.
    """
    import copy
    eff = copy.deepcopy(generic)
    eff.setdefault("ambiguous", {})
    eff.setdefault("source_verb_hints", {})
    meta = {"subject": subject, "generic": str(GENERIC_VERBS), "overlay": str(overlay_path) if overlay_path else None,
            "decision": (overlay or {}).get("decision"), "overrides": []}
    if not overlay:
        eff["_effective"] = meta
        return eff

    # collect overlay verb -> levels (by stem)
    ov: dict[str, list[str]] = {}
    for lvl, verbs in (overlay.get("verbs") or {}).items():
        for v in verbs:
            ov.setdefault(stem_verb(v), [])
            if lvl not in ov[stem_verb(v)]:
                ov[stem_verb(v)].append(lvl)
    for v, lvls in (overlay.get("ambiguous") or {}).items():
        ov[stem_verb(v)] = list(lvls)

    for verb, lvls in ov.items():
        was_levels = [l for l, vs in eff["verbs"].items() if any(stem_verb(x) == verb for x in vs)]
        was_amb = next((k for k in eff["ambiguous"] if stem_verb(k) == verb), None)
        was_hint = next((eff["source_verb_hints"][k] for k in eff["source_verb_hints"]
                         if not k.startswith("_") and stem_verb(k) == verb), None)
        for l in eff["verbs"]:
            eff["verbs"][l] = [x for x in eff["verbs"][l] if stem_verb(x) != verb]
        if was_amb is not None:
            del eff["ambiguous"][was_amb]
        for l in lvls:
            eff["verbs"].setdefault(l, []).append(verb)
        if len(lvls) > 1:
            eff["ambiguous"][verb] = list(lvls)
        for k in [k for k in eff["source_verb_hints"] if not k.startswith("_") and stem_verb(k) == verb]:
            del eff["source_verb_hints"][k]
        eff["source_verb_hints"][verb] = lvls[0] if len(lvls) == 1 else max(lvls, key=bloom_rank)
        changed = sorted(was_levels) != sorted(lvls) or (was_amb is not None and len(lvls) == 1) \
            or (was_hint is not None and was_hint != eff["source_verb_hints"][verb])
        meta["overrides"].append({"verb": verb, "level": lvls if len(lvls) > 1 else lvls[0],
                                  "generic_levels": was_levels, "generic_ambiguous": bool(was_amb),
                                  "generic_hint": was_hint, "changed": changed})
    for f in overlay.get("forbidden_criterion_verbs_extra") or []:
        if f.lower() not in [x.lower() for x in eff["forbidden_criterion_verbs"]]:
            eff["forbidden_criterion_verbs"].append(f)
    eff["_effective"] = meta
    return eff


def load_bloom_rules(subject: str | None = None) -> dict:
    """The effective verb table for a subject (generic when the subject has no table)."""
    generic = load_json(GENERIC_VERBS)
    op = subject_verb_table_path(subject)
    overlay = load_json(op) if op else None
    return merge_verb_rules(generic, overlay, subject, op)


def validate_schema(data, schema_name: str) -> list[str]:
    """Return a list of schema error messages (empty when valid)."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return ["jsonschema not installed: pip install jsonschema"]
    schema = load_json(SCHEMAS / schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))]


class Report:
    """Collects findings with severity; exit code 1 on any 'fail'."""

    def __init__(self, name: str):
        self.name = name
        self.items: list[tuple[str, str, str]] = []  # (severity, rule, message)

    def fail(self, rule: str, msg: str) -> None:
        self.items.append(("fail", rule, msg))

    def warn(self, rule: str, msg: str) -> None:
        self.items.append(("warn", rule, msg))

    def info(self, rule: str, msg: str) -> None:
        self.items.append(("info", rule, msg))

    @property
    def failed(self) -> bool:
        return any(s == "fail" for s, _, _ in self.items)

    def print_and_exit(self, json_out: str | None = None) -> None:
        counts = {s: sum(1 for x in self.items if x[0] == s) for s in ("fail", "warn", "info")}
        print(f"[{self.name}] fail={counts['fail']} warn={counts['warn']} info={counts['info']}")
        for sev, rule, msg in self.items:
            print(f"  {sev.upper():5} {rule:4} {msg}")
        if json_out:
            save_json(json_out, {"name": self.name, "failed": self.failed,
                                 "items": [{"severity": s, "rule": r, "message": m} for s, r, m in self.items]})
        sys.exit(1 if self.failed else 0)
