#!/usr/bin/env python3
"""Pattern catalogue: validate, merge, add and retire patterns (specs/31 §1, §6).

Usage:
  patterns.py validate [<subject> ...]                 schema + cross checks of knobs.json, the base layer and the
                                                       subject layers (default: every subject with toets/patterns.json)
  patterns.py merged   <subject> [--out <file>]        base + subject layer as one catalogue (R/30_patterns.json)
  patterns.py add      <subject|base> <decision-id> <record.json>
                                                       add or change one pattern record; refuses unless <decision-id> is an
                                                       *answered* decision (base: of any subject, subject: of that subject)
  patterns.py retire   <code> <decision-id>            mark a pattern 'retired' (never deleted: labels still refer to it)

Options: --subjects <dir> replaces subjects/, --base <file> replaces data/toets/patterns_base.json,
--knobs <file> replaces data/toets/knobs.json (used by the fixture test).
Nothing else writes the catalogue files.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from tcommon import (BASE_PATTERNS_PATH, KNOBS_PATH, ROOT, knob_index, load_json, merged_catalogue, save_json,
                     subject_patterns_path, validate_def, validate_schema)


class Ctx:
    def __init__(self, argv: list[str]):
        def opt(flag: str) -> str | None:
            return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None
        self.subjects = Path(opt("--subjects")) if opt("--subjects") else ROOT / "subjects"
        self.base = Path(opt("--base")) if opt("--base") else BASE_PATTERNS_PATH
        self.knobs = Path(opt("--knobs")) if opt("--knobs") else KNOBS_PATH
        self.out = opt("--out")
        drop = {"--subjects", "--base", "--knobs", "--out"}
        self.args, skip = [], False
        for a in argv[1:]:
            if skip:
                skip = False
            elif a in drop:
                skip = True
            else:
                self.args.append(a)

    def subject_layers(self) -> list[str]:
        if not self.subjects.exists():
            return []
        return sorted(p.name for p in self.subjects.iterdir() if (p / "toets" / "patterns.json").exists())


def check_layer(doc: dict, expected_layer: str, knobs: dict, label: str) -> list[str]:
    errs = [f"{label}: {e}" for e in validate_schema(doc, "patterns.schema.json")]
    if errs:
        return errs
    if doc["layer"] != expected_layer:
        errs.append(f"{label}: layer '{doc['layer']}' but the file belongs to '{expected_layer}'")
    seen = set()
    for p in doc["patterns"]:
        tag = f"{label} {p['code']}"
        if p["code"] in seen:
            errs.append(f"{tag}: duplicate code")
        seen.add(p["code"])
        if p["layer"] != doc["layer"]:
            errs.append(f"{tag}: record layer '{p['layer']}' != file layer '{doc['layer']}'")
        if p["points"][0] > p["points"][1]:
            errs.append(f"{tag}: points range {p['points']} is not [min, max]")
        for k, v in p["knobs_fixed"].items():
            kd = knobs.get(k)
            if not kd:
                errs.append(f"{tag}: knobs_fixed '{k}' is not a knob")
            elif not kd["settable"]:
                errs.append(f"{tag}: knobs_fixed '{k}' is a computed knob")
            elif kd["values"] != "catalogue" and v not in kd["values"]:
                errs.append(f"{tag}: knobs_fixed {k}='{v}' not in {kd['values']}")
            elif isinstance(kd["applies_to_kinds"], list) and p["kind"] not in kd["applies_to_kinds"]:
                errs.append(f"{tag}: knobs_fixed '{k}' does not apply to kind '{p['kind']}'")
        if p["status"] == "retired" and not p.get("retired_by"):
            errs.append(f"{tag}: retired without retired_by")
    return errs


def check_knobs(doc: dict) -> list[str]:
    errs = [f"knobs.json: {e}" for e in validate_schema(doc, "knobs.schema.json")]
    ids = [k["id"] for k in doc.get("knobs", [])]
    if len(ids) != len(set(ids)):
        errs.append("knobs.json: duplicate knob id")
    for k in doc.get("knobs", []):
        if isinstance(k.get("definition"), dict) and isinstance(k.get("values"), list):
            extra = set(k["definition"]) - set(k["values"])
            if extra:
                errs.append(f"knobs.json {k['id']}: definition for unknown values {sorted(extra)}")
    return errs


def validate_all(ctx: Ctx, subjects: list[str]) -> list[str]:
    knobs_doc = load_json(ctx.knobs)
    errs = check_knobs(knobs_doc)
    knobs = knob_index(knobs_doc) if not errs else {}
    base = load_json(ctx.base)
    errs += check_layer(base, "base", knobs, "base")
    base_codes = {p["code"] for p in base.get("patterns", [])}
    for s in subjects:
        path = subject_patterns_path(s, ctx.subjects)
        if not path.exists():
            errs.append(f"{s}: no {path}")
            continue
        doc = load_json(path)
        errs += check_layer(doc, s, knobs, s)
        for p in doc.get("patterns", []):
            if p.get("code") in base_codes:
                errs.append(f"{s} {p['code']}: code also in the base layer")
    return errs


def answered_decision(ctx: Ctx, did: str, layer: str) -> dict:
    subjects = ctx.subject_layers_all() if layer == "base" else [layer]
    for s in subjects:
        dp = ctx.subjects / s / "decisions.json"
        if not dp.exists():
            continue
        dec = next((d for d in load_json(dp)["decisions"] if d["id"] == did), None)
        if dec:
            if dec["status"] != "answered":
                sys.exit(f"decision {did} has status {dec['status']!r}; only an answered decision can change the catalogue")
            return dec
    sys.exit(f"decision {did} not found in {'any subject' if layer == 'base' else layer}/decisions.json")


def _all_subjects(self: Ctx) -> list[str]:
    return sorted(p.name for p in self.subjects.iterdir() if (p / "decisions.json").exists()) if self.subjects.exists() else []


Ctx.subject_layers_all = _all_subjects


def layer_path(ctx: Ctx, layer: str) -> Path:
    return ctx.base if layer == "base" else subject_patterns_path(layer, ctx.subjects)


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def cmd_add(ctx: Ctx, layer: str, did: str, record_path: str) -> None:
    answered_decision(ctx, did, layer)
    path = layer_path(ctx, layer)
    if path.exists():
        doc = load_json(path)
    elif layer != "base" and (ctx.subjects / layer).exists():
        doc = {"layer": layer, "version": f"decisions-{today()}", "patterns": []}
    else:
        sys.exit(f"no catalogue layer '{layer}' ({path})")
    rec = load_json(record_path)
    rec.setdefault("layer", layer)
    rec.setdefault("status", "active")
    rec.setdefault("examples_seed", [])
    rec.setdefault("knobs_fixed", {})
    rec.update(source="decision", decision=did, added_at=today())
    if rec["layer"] != layer:
        sys.exit(f"record layer '{rec['layer']}' != target layer '{layer}'")
    # base codes are global: a subject code may not be a base code and vice versa (subject layers may share codes)
    clash = [s for s in ctx.subject_layers() if layer == "base"] if layer == "base" else ["base"]
    for o in clash:
        op = layer_path(ctx, o)
        if op.exists() and any(p["code"] == rec.get("code") for p in load_json(op)["patterns"]):
            sys.exit(f"code {rec.get('code')} already exists in layer '{o}'")
    replaced = any(p["code"] == rec.get("code") for p in doc["patterns"])
    doc["patterns"] = [p for p in doc["patterns"] if p["code"] != rec.get("code")] + [rec]
    doc["patterns"].sort(key=lambda p: p["code"])
    errs = check_layer(doc, layer, knob_index(load_json(ctx.knobs)), layer)
    if errs:
        sys.exit("refusing to write an invalid catalogue:\n  " + "\n  ".join(errs))
    save_json(path, doc)
    print(f"[patterns] {'changed' if replaced else 'added'} {rec['code']} in layer {layer} (decision {did})")


def cmd_retire(ctx: Ctx, code: str, did: str) -> None:
    for layer in ["base"] + ctx.subject_layers():
        path = layer_path(ctx, layer)
        doc = load_json(path)
        rec = next((p for p in doc["patterns"] if p["code"] == code), None)
        if not rec:
            continue
        answered_decision(ctx, did, layer)
        if rec["status"] == "retired":
            sys.exit(f"{code} is already retired (by {rec.get('retired_by')})")
        rec.update(status="retired", retired_by=did, retired_at=today())
        errs = check_layer(doc, layer, knob_index(load_json(ctx.knobs)), layer)
        if errs:
            sys.exit("refusing to write an invalid catalogue:\n  " + "\n  ".join(errs))
        save_json(path, doc)
        print(f"[patterns] retired {code} in layer {layer} (decision {did})")
        return
    sys.exit(f"pattern {code} not found in any layer")


def main(argv: list[str]) -> None:
    ctx = Ctx(argv)
    a = ctx.args
    if not a:
        print(__doc__)
        sys.exit(2)
    cmd = a[0]
    if cmd == "validate":
        subjects = a[1:] or ctx.subject_layers()
        errs = validate_all(ctx, subjects)
        if errs:
            print(f"[patterns] invalid ({len(errs)}):\n  " + "\n  ".join(errs))
            sys.exit(1)
        n = len(load_json(ctx.base)["patterns"]) + sum(len(load_json(subject_patterns_path(s, ctx.subjects))["patterns"])
                                                     for s in subjects)
        print(f"[patterns] valid: knobs, base + {', '.join(subjects) or 'no subject layers'} ({n} patterns)")
    elif cmd == "merged" and len(a) == 2:
        errs = validate_all(ctx, [a[1]] if subject_patterns_path(a[1], ctx.subjects).exists() else [])
        if errs:
            sys.exit("[patterns] invalid catalogue:\n  " + "\n  ".join(errs))
        cat = merged_catalogue(a[1], ctx.base, ctx.subjects)
        errs = validate_def(cat, "patterns.schema.json", "merged")
        if errs:
            sys.exit("[patterns] merged catalogue invalid:\n  " + "\n  ".join(errs))
        if ctx.out:
            save_json(ctx.out, cat)
            print(f"[patterns] merged {len(cat['patterns'])} patterns ({', '.join(cat['layers'])}) -> {ctx.out}")
        else:
            import json
            print(json.dumps(cat, ensure_ascii=False, indent=1))
    elif cmd == "add" and len(a) == 4:
        cmd_add(ctx, a[1], a[2], a[3])
    elif cmd == "retire" and len(a) == 3:
        cmd_retire(ctx, a[1], a[2])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
