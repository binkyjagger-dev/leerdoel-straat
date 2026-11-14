#!/usr/bin/env python3
"""E7 / T4 — merge pattern and knob labels A/B (+R) into one record per question (specs/26 §3, specs/34 §4).

Usage: label_merge.py <run_dir> [--toets] [--bank <dir>] [--subjects <dir>]

Exam mode (default, an /examen run): reads 26_labels.<A|B|R>/<opgave>.json, 21_exam_units.json (+ text/) and the
links (24_mappings.json, or the bank's links/ when the run has none: /examen --label). Writes 26_labels.json,
26_label_findings.json and 26_proposed_patterns.json.
Toets mode (--toets, a /toets run, specs/33 §4): reads 34_labels.<A|B|R>/<opgave>.json, 33_items/, 32_blueprint.json,
30_criteria.json, 30_patterns.json, 30_knobs.json. Writes 34_labels.json, 34_label_findings.json and
34_proposed_patterns.json.

Agreement per field: equal → high; ordinal fields with ≥ 3 values one step apart → medium and the lower value;
otherwise disputed (two-valued knobs never medium)
(value null). `pattern` must agree exactly (a '+'-combination in any order). R decides the fields it gives; its
decision is final (confidence high, listed in repaired_fields). Points come from the units/items (LB6), never from a
labeller; `combination` and `bloom` are computed from the links. A knob that does not apply to the merged pattern's
kind (or to the first question of an opgave) is null.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from lcommon import PREFIX, Run, bank_dir, subjects_dir, computed_fields, load_labeller
from ecommon import Report, load_json, save_json, validate_def
from tcommon import EXAMPLE_QUALITY, LABEL_FIELDS, LABEL_KNOBS, kinds_of, knob_applies, same_pattern

# specs/26 §3.2 (bouwvraag 1, decided 2026-11-13): only ordinal fields with three or more values get `medium` for
# one step apart; on a two-valued knob (claim, new_concept, builds_on, route, schema) any difference is disputed.
MIN_VALUES_FOR_MEDIUM = 3


def merge_field(field: str, a, b, order: list[str] | None) -> tuple[object, str]:
    if field == "pattern":
        return (a, "high") if same_pattern(a, b) else (None, "disputed")
    if a == b:
        return a, "high"
    if order and a in order and b in order and len(order) >= MIN_VALUES_FOR_MEDIUM \
            and abs(order.index(a) - order.index(b)) == 1:
        return min(a, b, key=order.index), "medium"
    return None, "disputed"


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(argv[1])
    mode = "toets" if "--toets" in argv else "exam"
    rep = Report("label_merge")
    run = Run(run_dir, mode, bank_dir(load_json(run_dir / "run.json")["subject"], argv), subjects_dir(argv))
    A, ea = load_labeller(run, "A")
    B, eb = load_labeller(run, "B")
    R, er = load_labeller(run, "R")
    for e in ea + eb + er:
        rep.fail("LB1", e)
    for letter, items in (("A", A), ("B", B)):
        missing = [q for q in run.questions if q not in items]
        if missing:
            rep.fail("LB1", f"labeller {letter} has no label for {len(missing)} questions, e.g. {missing[:3]}")
    for letter, items in (("A", A), ("B", B), ("R", R)):
        for qid in items:
            if qid not in run.questions:
                rep.fail("LB1", f"labeller {letter}: unknown question {qid}")
    if rep.failed:
        rep.print_and_exit()

    orders = {k: (run.knobs[k]["values"] if run.knobs[k]["ordinal"] else None) for k in LABEL_KNOBS}
    orders["example_quality"] = EXAMPLE_QUALITY
    labels, findings, proposals = [], [], []
    for qid, q in run.questions.items():
        a, b, r = A[qid], B[qid], R.get(qid)
        rec = {"exam_id": q["exam_id"], "question_id": qid, "question_number": q["question_number"],
               "opgave_id": q["opgave_id"], "first_of_opgave": q["first_of_opgave"], "points": q["points"]}
        conf, evidence, repaired, disagreements = {}, {}, [], {}
        fields = LABEL_FIELDS + (["example_quality"] if mode == "exam" else [])
        for f in fields:
            val, c = merge_field(f, a.get(f), b.get(f), orders.get(f))
            src = a if val == a.get(f) else b
            if c != "high":
                disagreements[f] = {"A": a.get(f), "B": b.get(f)}
            if r is not None and f in r:
                val, c, src = r[f], "high", r
                repaired.append(f)
                disagreements.setdefault(f, {"A": a.get(f), "B": b.get(f)})["R"] = r[f]
            rec[f], conf[f] = val, c
            if f in (src.get("evidence") or {}) and val is not None:
                evidence[f] = src["evidence"][f]
            if c != "high":
                findings.append({"question_id": qid, "field": f, "confidence": c, "A": a.get(f), "B": b.get(f)})
        if mode == "toets":
            rec["example_quality"] = None
        # applicability (specs/31 §2): a knob that does not apply to the merged pattern is null
        kinds = kinds_of(rec["pattern"], run.pidx)
        if rec["pattern"] is not None and rec["pattern"] != "NIEUW":
            for k in ("route", "schema", "builds_on"):
                if not knob_applies(run.knobs[k], kinds, q["first_of_opgave"]) and rec[k] is not None:
                    rec[k], conf[k] = None, "high"
                    evidence.pop(k, None)
        elif q["first_of_opgave"]:
            rec["builds_on"] = None
        # builds_on_questions: R's when it decided builds_on, else the union over the labellers that said 'ja'
        if rec["builds_on"] == "ja":
            if r is not None and "builds_on" in r:
                rec["builds_on_questions"] = sorted(set(r.get("builds_on_questions") or []))
            else:
                rec["builds_on_questions"] = sorted({n for x in (a, b) if x.get("builds_on") == "ja"
                                                     for n in x.get("builds_on_questions") or []})
        else:
            rec["builds_on_questions"] = []
        # a new pattern: keep the proposal(s)
        rec["proposed_pattern"] = None
        if rec["pattern"] == "NIEUW":
            src = r if r is not None and "pattern" in r else a
            rec["proposed_pattern"] = src.get("proposed_pattern")
        for letter, x in (("A", a), ("B", b), ("R", r)):
            if x is not None and x.get("pattern") == "NIEUW" and x.get("proposed_pattern"):
                proposals.append({"question_id": qid, "opgave_id": q["opgave_id"], "exam_id": q["exam_id"],
                                  "question_number": q["question_number"], "labeller": letter,
                                  "proposed_pattern": x["proposed_pattern"]})
        quality_src = r if r is not None and "example_quality" in r else (a if rec["example_quality"] == a.get("example_quality") else b)
        rec["example_quality_reason"] = quality_src.get("example_quality_reason") if rec["example_quality"] else None
        rec.update(computed_fields(run.links_of(qid)))
        rec.update(confidence=conf, evidence=evidence, repaired_fields=repaired, disagreements=disagreements)
        labels.append(rec)

    labels.sort(key=lambda x: (x["exam_id"] or "", x["question_number"]))
    out = {"mode": mode, "run_id": run.run.get("run_id", run_dir.name), "labels": labels, "proposed_patterns": proposals}
    for e in validate_def(out, "item_labels.schema.json", "merged")[:5]:
        rep.fail("LB1", e)
    if rep.failed:
        rep.print_and_exit()
    p = PREFIX[mode]
    save_json(run_dir / f"{p}.json", out)
    save_json(run_dir / f"{p.replace('labels', 'label_findings')}.json", {"findings": findings})
    save_json(run_dir / f"{p.replace('labels', 'proposed_patterns')}.json", decision_questions(run.subject, proposals))
    cnt = Counter(c for l in labels for c in l["confidence"].values())
    left = sum(1 for l in labels for c in l["confidence"].values() if c == "disputed")
    rep.info("LB1", f"{len(labels)} questions merged ({mode}); field confidence {dict(cnt)}; "
                    f"{sum(1 for l in labels if l['repaired_fields'])} repaired by R; {left} disputed fields left")
    rep.info("LB2", f"patterns {dict(Counter(l['pattern'] for l in labels))}; {len(proposals)} new-pattern proposals")
    if left:
        per = Counter(l["opgave_id"] for l in labels if "disputed" in l["confidence"].values() and not l["repaired_fields"])
        if per:
            rep.info("LB1", f"opgaven for the R round: {', '.join(sorted(per))}")
    rep.print_and_exit()


def decision_questions(subject: str, proposals: list[dict]) -> dict:
    """26_proposed_patterns.json in the intake-questions format, ready for decisions.py add (open, catalogue)."""
    seen, qs = set(), []
    for p in proposals:
        pp = p["proposed_pattern"]
        key = (pp["name"].strip().lower(), pp.get("layer"))
        if key in seen:
            continue
        seen.add(key)
        where = f"{p['exam_id']} vraag {p['question_number']}" if p["exam_id"] else f"vraag {p['question_number']}"
        qs.append({"key": f"nieuw-patroon-{len(qs) + 1}",
                   "question": f"Nieuw vraagpatroon '{pp['name']}' toevoegen aan de catalogus (laag {pp.get('layer')})?",
                   "context": f"Voorgesteld door labeller {p['labeller']} bij {where}. Omschrijving: {pp['description']} "
                              f"Scoring: {pp['scoring']}. Soort: {pp.get('kind') or 'onbekend'}.",
                   "options": ["Toevoegen zoals voorgesteld", "Toevoegen met aanpassing", "Niet toevoegen (bestaand patroon)"],
                   "proposed": "Toevoegen zoals voorgesteld", "impact": "low", "applies_to": ["catalogue"],
                   "affects_units": sorted({x["question_id"] for x in proposals if x["proposed_pattern"]["name"] == pp["name"]})})
    return {"subject": subject, "questions": qs, "proposals": proposals}


if __name__ == "__main__":
    main(sys.argv)
