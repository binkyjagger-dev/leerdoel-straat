#!/usr/bin/env python3
"""T3 — checks IT1–IT7 on one opgave written by the toets-writer (specs/34 §3).

Usage: items_check.py <run_dir> --opgave <id> [--subjects <dir>]

IT1 schema toets_items; vraag ids, numbers and points = blueprint; scorepunten (seq, points, criterion) = blueprint
IT2 cv: maximumscore = points; scorepunt points sum to it; every scorepunt has text
IT3 every number in intro, stems, sources, tables and the uitwerkbijlage is a `data` value; every number in a model
    answer is a `data` value or a calc `shown` value (Dutch notation; "21%" matches 0.21 or 21; reference numbers
    such as "informatiebron 2" and "vraag 3" are skipped; 0, 1, 100 and years 1900–2100 written as a plain
    four-digit number are always allowed — bouwvraag 11)
IT4 noise_data only when a vraag of the opgave has sources = "meerdere bronnen met ruis", and then not empty;
    uses_data / noise_data keys exist in data; every uses_data key is used by a calc or named in a model answer
IT5 builds_on_vragen = blueprint; with builds_on = ja the cv has a follow_through sentence and a calc uses a calc
    name of an earlier vraag — or, for a vraag without calc, the stem names "vraag n" for an n in builds_on_vragen
IT6 conventions: "€ " with a space; btw value = the order's / conventions.md default (warning: a context may need
    another rate); a stem names "informatiebron n" for every source whose data its calcs use; a schema vraag
    mentions the uitwerkbijlage
IT7 the stem's asking verb fits the pattern's stem_forms (warning, like MB2)
Writes 33_checks/<opgave>.json.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from nlnum import REF_RE, close, names_in, scan_numbers, shown_value
from tcommon import Report, kinds_of, load_json, pattern_codes, validate_schema
from toetsrun import ToetsRun, opt, subjects_opt

EXEMPT = {0.0, 1.0, 100.0}  # bouwvraag 11 (decided 2026-11-14): plus years 1900–2100, see is_year
YEAR_RE = re.compile(r"^(19\d\d|20\d\d|2100)$")


def is_year(lit: str, pct: bool) -> bool:
    return not pct and bool(YEAR_RE.match(lit))


def texts_of(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return [str(obj).replace(".", ",")]
    if isinstance(obj, list):
        return [t for x in obj for t in texts_of(x)]
    if isinstance(obj, dict):
        return [t for x in obj.values() for t in texts_of(x)]
    return []


def matches(lit_val: float, pct: bool, pool: list[float], lit: str = "") -> bool:
    if lit_val in EXEMPT or is_year(lit, pct):
        return True
    return any(close(lit_val, d) or (pct and close(lit_val / 100, d)) for d in pool)


def referenced_sources(stem: str) -> set[int]:
    out = set()
    for m in REF_RE.finditer(stem):
        if m.group(0).lower().startswith(("informatiebron", "bron")):
            out |= {int(x) for x in re.findall(r"\d+", m.group(0))}
    return out


def main(argv: list[str]) -> None:
    if len(argv) < 2 or not opt(argv, "--opgave"):
        print(__doc__)
        sys.exit(2)
    R, oid = Path(argv[1]), opt(argv, "--opgave")
    rep = Report(f"items_check {oid}")
    run = ToetsRun(R, subjects_opt(argv))
    out_json = str(R / "33_checks" / f"{oid}.json")
    (R / "33_checks").mkdir(exist_ok=True)
    it = load_json(R / "33_items" / f"{oid}.json")
    errs = validate_schema(it, "toets_items.schema.json")
    for e in errs[:10]:
        rep.fail("IT1", e)
    if errs:
        rep.print_and_exit(out_json)
    bp = run.blueprint()
    og = next((o for o in bp["opgaven"] if o["opgave_id"] == oid), None)
    if not og or it["opgave_id"] != oid:
        rep.fail("IT1", f"opgave {oid} not in the blueprint or the file holds {it['opgave_id']}")
        rep.print_and_exit(out_json)
    bv = {v["vraag_id"]: v for v in og["vragen"]}
    iv = {v["vraag_id"]: v for v in it["vragen"]}
    # IT1
    if set(bv) != set(iv):
        rep.fail("IT1", f"vragen {sorted(iv)} != blueprint {sorted(bv)}")
    for vid in sorted(set(bv) & set(iv)):
        b, v = bv[vid], iv[vid]
        if (v["number"], v["points"]) != (b["number"], b["points"]):
            rep.fail("IT1", f"{vid}: number/points {v['number']}/{v['points']} != blueprint {b['number']}/{b['points']}")
        a = [(s["seq"], s["points"], s["criterion_id"]) for s in v["cv"]["scorepunten"]]
        e = [(s["seq"], s["points"], s["criterion_id"]) for s in b["scorepunten"]]
        if a != e:
            rep.fail("IT1", f"{vid}: scorepunten {a} != blueprint {e}")
    # IT2
    for vid, v in iv.items():
        cv = v["cv"]
        if cv["maximumscore"] != v["points"]:
            rep.fail("IT2", f"{vid}: maximumscore {cv['maximumscore']} != points {v['points']}")
        if sum(s["points"] for s in cv["scorepunten"]) != cv["maximumscore"]:
            rep.fail("IT2", f"{vid}: scorepunten sum to {sum(s['points'] for s in cv['scorepunten'])}, maximumscore {cv['maximumscore']}")
        for s in cv["scorepunten"]:
            if not s["text"].strip():
                rep.fail("IT2", f"{vid} s{s['seq']}: scorepunt without text")
    # IT3
    data = it["data"]
    pool = list(data.values())
    shown = []
    for v in it["vragen"]:
        for c in v["cv"]["calc"]:
            try:
                shown.append(shown_value(c["shown"])[0])
            except ValueError:
                pass
    student_parts = [("intro", it["intro"])] + [(f"{v['vraag_id']} stem", v["stem"]) for v in it["vragen"]]
    for s in it["sources"]:
        student_parts += [(f"informatiebron {s['n']}", t) for t in texts_of([s.get("title"), s.get("text"), s.get("table")])]
    for v in it["vragen"]:
        if v.get("uitwerkbijlage"):
            student_parts += [(f"{v['vraag_id']} uitwerkbijlage", t) for t in texts_of(v["uitwerkbijlage"])]
    for where, text in student_parts:
        for lit, val, pct in scan_numbers(text):
            if not matches(val, pct, pool, lit):
                rep.fail("IT3", f"{where}: number '{lit}' is not in data (name every given number in data)")
    for v in it["vragen"]:
        for lit, val, pct in scan_numbers(v["cv"]["model_answer"]):
            if not matches(val, pct, pool + shown, lit):
                rep.fail("IT3", f"{v['vraag_id']} model answer: number '{lit}' is neither data nor a calc's shown value")
    # IT4
    calc_names = set()
    for v in it["vragen"]:
        for c in v["cv"]["calc"]:
            calc_names |= names_in(c["expr"])
    noisy = any(b["knobs"].get("sources") == "meerdere bronnen met ruis" for b in bv.values())
    noise = [k for s in it["sources"] for k in s.get("noise_data", [])]
    if noise and not noisy:
        rep.fail("IT4", f"noise_data {noise} but no vraag of {oid} has sources = meerdere bronnen met ruis")
    if noisy and not noise:
        rep.fail("IT4", f"a vraag of {oid} has sources = meerdere bronnen met ruis but no source has noise_data")
    answers = " ".join(v["cv"]["model_answer"] for v in it["vragen"])
    for s in it["sources"]:
        for k in s.get("uses_data", []) + s.get("noise_data", []):
            if k not in data:
                rep.fail("IT4", f"informatiebron {s['n']}: '{k}' is not a data key")
        for k in s.get("uses_data", []):
            if k in data and k not in calc_names and not any(close(val, data[k]) for _, val, _ in scan_numbers(answers)):
                rep.fail("IT4", f"informatiebron {s['n']}: uses_data '{k}' is used by no calc and not named in a model answer")
        for k in s.get("noise_data", []):
            if k in calc_names:
                rep.warn("IT4", f"informatiebron {s['n']}: noise_data '{k}' is used by a calc")
    # IT5
    defined_in = {}
    for v in sorted(it["vragen"], key=lambda x: x["number"]):
        for c in v["cv"]["calc"]:
            defined_in[c["name"]] = v["number"]
    for vid, v in iv.items():
        b = bv.get(vid)
        if not b:
            continue
        if sorted(v["builds_on_vragen"]) != sorted(b["builds_on_vragen"]):
            rep.fail("IT5", f"{vid}: builds_on_vragen {v['builds_on_vragen']} != blueprint {b['builds_on_vragen']}")
        if b["knobs"].get("builds_on") == "ja":
            if v["cv"]["calc"]:
                used = set().union(*(names_in(c["expr"]) for c in v["cv"]["calc"]))
                if not any(defined_in.get(n, v["number"]) < v["number"] for n in used):
                    rep.fail("IT5", f"{vid}: builds_on = ja but no calc uses a result of an earlier vraag")
            else:  # a vraag without calc builds on via "vraag n" in the stem (bouwvraag 17)
                named = {int(n) for m in re.finditer(r"\bvra(?:a|ge)g(?:en)?\s+\d+(?:\s*(?:,|en)\s*\d+)*", v["stem"], re.I)
                         for n in re.findall(r"\d+", m.group(0))}
                if not named & set(b["builds_on_vragen"]):
                    rep.fail("IT5", f"{vid}: builds_on = ja, no calc, and the stem names none of vraag "
                                    f"{', '.join(map(str, b['builds_on_vragen']))}")
            if not (v["cv"].get("follow_through") or "").strip():
                rep.fail("IT5", f"{vid}: builds_on = ja but the cv has no follow_through sentence")
    # IT6
    btw = run.btw_default()
    for k, val in data.items():
        if "btw" in k.lower() and btw is not None and not close(val, btw):
            rep.warn("IT6", f"data '{k}' = {val} but the btw default is {btw} (fine when the context needs another rate)")
    for where, text in student_parts + [(f"{v['vraag_id']} model answer", v["cv"]["model_answer"]) for v in it["vragen"]]:
        if re.search(r"€\d", text):
            rep.fail("IT6", f"{where}: write '€ 12,50' (euro sign, space, amount)")
        if re.search(r"(?<![\d.,])\d+\.\d{1,2}(?![\d.,])", text):
            rep.warn("IT6", f"{where}: a decimal point? Dutch notation uses a comma ('12,50')")
    for vid, v in iv.items():
        used = set().union(*(names_in(c["expr"]) for c in v["cv"]["calc"])) if v["cv"]["calc"] else set()
        need = {s["n"] for s in it["sources"] if used & set(s.get("uses_data", []))}
        missing = need - referenced_sources(v["stem"])
        if missing:
            rep.fail("IT6", f"{vid}: the stem does not name informatiebron {', '.join(map(str, sorted(missing)))} whose data it uses")
        b = bv.get(vid)
        if b and "schema" in kinds_of(b["pattern"], run.pidx) and "uitwerkbijlage" not in v["stem"].lower():
            rep.fail("IT6", f"{vid}: schema vraag without the uitwerkbijlage sentence")
    # IT7
    for vid, v in iv.items():
        b = bv.get(vid)
        if not b:
            continue
        verbs = {f.split()[0].strip("….").lower() for c in pattern_codes(b["pattern"]) if c in run.pidx
                 for f in run.pidx[c]["stem_forms"] if f.split() and f.split()[0][0].isupper()}
        if verbs and not any(re.search(rf"\b{re.escape(x)}\b", v["stem"].lower()) for x in verbs):
            rep.warn("IT7", f"{vid}: stem has none of the asking verbs of {b['pattern']} ({', '.join(sorted(verbs))})")
    rep.info("IT1", f"{oid}: {len(it['vragen'])} vragen, {len(data)} data values, {len(it['sources'])} sources checked")
    rep.print_and_exit(out_json)


if __name__ == "__main__":
    main(sys.argv)
