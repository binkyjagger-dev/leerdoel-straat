"""specs/36 §5–§6: the house-rule checks on written items — IT8 (question form), IT9 (cue scan), IT10 (term giveaway),
IT11 (lead size) and RB (reading budget) — shared by items_check.py (the checks) and export_toets.py (the
verantwoording's section *Huisregels*). Measures with the same instrument as exam_metrics.py (tasks.py).

Rules in data: data/toets/asking_verbs.json and data/toets/cue_phrases.json, each with a subject overlay in
subjects/<s>/toets/. House rules: the reference profile's `house_rules` (30_reference_profile.json); without them
every CE limit is an info line, never a failure (§11 B14). Reused opgaven are exempt per opgave (§11 B13).
"""
from __future__ import annotations

import re
from pathlib import Path

from tasks import count_tasks, is_helper, load_rules, new_numbers, sentences, starts_with_verb, task_form_ok, words
from tcommon import ROOT, lead_task, load_json

CUE_PATH = ROOT / "data" / "toets" / "cue_phrases.json"
RB_MARGIN = 1.1
LOW_BLOOM = ("onthouden",)  # IT10 error level (decided 2026-11-17); higher = warning to V11
WORD = re.compile(r"[a-zà-ÿ0-9]+")


def load_cues(subject: str | None = None, subjects: Path | None = None) -> dict:
    base = load_json(CUE_PATH)
    out = {k: list(base[k]) for k in ("route", "direction", "allow")}
    if subject:
        ov = (subjects or ROOT / "subjects") / subject / "toets" / "cue_phrases.json"
        if ov.exists():
            o = load_json(ov)
            for k in out:
                out[k] += [x for x in o.get(k, []) if x not in out[k]]
    for k in ("route", "direction", "allow"):
        out[k] = [{**r, "re": re.compile(r["pattern"], re.I)} for r in out[k]]
    return out


def source_text(s: dict) -> str:
    parts = [s.get("title") or "", s.get("text") or ""]
    for row in s.get("table") or []:
        parts += [str(c) for c in row if c is not None]
    return "\n".join(p for p in parts if p)


def opgave_words(it: dict) -> dict:
    """Words of intro, sources, leads and tasks (§11 B9: whitespace tokens, table cells included)."""
    w = {"intro": words(it.get("intro")), "sources": sum(words(source_text(s)) for s in it.get("sources") or []),
         "leads": 0, "tasks": 0}
    for v in it["vragen"]:
        lead, task = lead_task(v)
        w["leads"] += words(lead)
        w["tasks"] += words(task)
    w["total"] = sum(w.values())
    return w


def budget(points: float, hr: dict | None, pct) -> float | None:
    """RB limit: points × CE words per point × pct × 1.1 (None without house rules or with pct null)."""
    if not hr or pct is None:
        return None
    return points * hr["words_per_point"]["pooled"] * pct / 100 * RB_MARGIN


# ---------------------------------------------------------------------------------------------------- IT9 cue scan
def cue_hits(text: str, cues: dict, kind: str) -> list[str]:
    allowed = [m.span() for a in cues["allow"] for m in a["re"].finditer(text or "")]
    out = []
    for c in cues[kind]:
        for m in c["re"].finditer(text or ""):
            if any(a <= m.start() and m.end() <= b for a, b in allowed):
                continue
            out.append(m.group(0))
    return out


# ------------------------------------------------------------------------------------------------ IT10 term giveaway
def split_concept(c: str) -> list[str]:
    return [x.strip().lower() for x in re.split(r"\s*/\s*", c) if x.strip()]


def concept_index(criteria_doc: dict, glossary: dict | None) -> dict[str, set[str]]:
    """criterion_id → concepts: the group's `concepts` ∪ glossary terms (with synonyms) found in the criterion text."""
    entries = (glossary or {}).get("entries") or []
    out = {}
    for g in criteria_doc["groups"]:
        gc = {x for c in g.get("concepts") or [] for x in split_concept(c)}
        for c in g["criteria"]:
            text = " ".join([c.get("text_expert") or "", c.get("text_student") or ""]).lower()
            gl = set()
            for e in entries:
                forms = [e["term"], *(e.get("synonyms") or [])]
                if any(has_term(text, f.lower()) for f in forms):
                    gl |= {f.lower() for f in forms}
            out[c["criterion_id"]] = gc | gl
    return out


def has_term(text: str, term: str) -> bool:
    return bool(term) and re.search(r"(?<![a-zà-ÿ0-9])" + re.escape(term) + r"(?![a-zà-ÿ0-9])", (text or "").lower()) is not None


ROUTE_WINDOW = 5  # words after a route cue that still belong to it ('met behulp van de cpi')


def route_spans(s: str, cues: dict) -> list[tuple[int, int]]:
    """Spans of route hints in one sentence: a route-cue match plus the next ROUTE_WINDOW words."""
    out = []
    for c in cues["route"]:
        for m in c["re"].finditer(s):
            end = m.end()
            for _ in range(ROUTE_WINDOW):
                w = WORD.search(s, end)
                if not w:
                    break
                end = w.end()
            out.append((m.start(), end))
    return out


def object_of_verb(task: str, term: str, rules: dict, cues: dict) -> bool:
    """True when every occurrence of `term` in the task lies in the object of an asking verb (specs/36 §6 IT10,
    decided 2026-11-17): in a sentence that starts with an asking verb everything after the verb is its object
    ('Leg uit hoe een lagere prijs tot een hogere omzet leidt', 'Omschrijf wat X is', 'Bereken de X'), except a
    route hint (a route-cue match of cue_phrases.json plus the next five words: 'met behulp van de cpi')."""
    found = False
    for s in sentences(task):
        low = s.lower()
        spans = route_spans(low, cues)
        for m in re.finditer(r"(?<![a-zà-ÿ0-9])" + re.escape(term) + r"(?![a-zà-ÿ0-9])", low):
            found = True
            if not starts_with_verb(s, rules) or is_helper(s, rules):
                return False
            if any(a <= m.start() < b for a, b in spans):
                return False
    return found


def giveaways(it: dict, bp_vragen: dict, concepts: dict[str, set[str]], rules: dict, cues: dict) -> list[dict]:
    """IT10 hits: {vraag_id, seq, concept, where, bloom, severity}."""
    hits = []
    intro = it.get("intro") or ""
    for v in it["vragen"]:
        b = bp_vragen.get(v["vraag_id"])
        if not b:
            continue
        lead, task = lead_task(v)
        skip = {c.lower() for c in v.get("new_concepts") or []}
        plan = {s["seq"]: s for s in b["scorepunten"]}
        answer = (v["cv"].get("model_answer") or "").lower()
        for sp in v["cv"]["scorepunten"]:
            bloom = (plan.get(sp["seq"]) or {}).get("bloom")
            for c in sorted(concepts.get(sp["criterion_id"], set())):
                if c in skip or not (has_term(sp["text"], c) or has_term(answer, c)):
                    continue
                where = [w for w, t in (("intro", intro), ("lead", lead)) if has_term(t, c)]
                if has_term(task, c) and not object_of_verb(task, c, rules, cues):
                    where.append("task")
                if where:
                    hits.append({"vraag_id": v["vraag_id"], "seq": sp["seq"], "concept": c, "where": where, "bloom": bloom,
                                 "severity": "fail" if bloom in LOW_BLOOM else "warn"})
    return hits


# ---------------------------------------------------------------------------------------------------- the checks
def check_opgave(rep, run, it: dict, og: dict, bv: dict, glossary: dict | None, all_items: dict) -> dict:
    """IT8–IT11 and RB on one opgave; returns the measured numbers (for the verantwoording)."""
    rules = load_rules(run.subject, run.subjects)
    cues = load_cues(run.subject, run.subjects)
    hr, pct = run.house, run.order.get("reading_budget_pct")
    oid = it["opgave_id"]
    measured = {"words": opgave_words(it), "tasks": {}, "giveaways": [], "cues": []}
    if og.get("reused_from"):
        rep.info("IT8", f"{oid}: reused opgave — IT8–IT11 and the per-opgave reading budget are not checked (§11 B13)")
        return measured
    if not hr:
        rep.info("IT8", "geen huisregels gemeten: task length, lead size and the reading budget are not checked (§11 B14)")
    wt_lim = (hr or {}).get("words_task", {}).get("p90")
    wl_p90 = (hr or {}).get("words_lead", {}).get("p90")
    nl_p90 = (hr or {}).get("numbers_lead", {}).get("p90")
    known = [it.get("intro") or ""] + [source_text(s) for s in it.get("sources") or []]
    for v in it["vragen"]:
        vid, b = v["vraag_id"], bv.get(v["vraag_id"])
        lead, task = lead_task(v)
        # IT8 form
        if "task" not in v:
            rep.fail("IT8", f"{vid}: no `task` (write `lead` and `task`, specs/36 §5.1)")
        if not task_form_ok(task, rules):
            rep.fail("IT8", f"{vid}: the task does not start with an asking verb and is not a question: '{task[:60]}'")
        if wt_lim and words(task) > wt_lim:
            rep.fail("IT8", f"{vid}: task has {words(task)} words; CE words_task p90 = {wt_lim:g}")
        n = count_tasks(task, rules)
        measured["tasks"][vid] = n
        if b is not None:
            planned = b.get("n_tasks")
            if planned is not None and n != planned:
                rep.fail("IT8", f"{vid}: {n} task(s) in the task, the blueprint plans {planned}")
            mt = run.max_tasks(b["pattern"])
            if mt is not None and n > mt:
                rep.fail("IT8", f"{vid}: {n} tasks > max_tasks {mt} of {b['pattern']} in the central exam")
        # IT11 lead
        if wl_p90 is not None and pct is not None and words(lead) > wl_p90 * pct / 100:
            rep.fail("IT11", f"{vid}: lead has {words(lead)} words; limit CE words_lead p90 {wl_p90:g} × {pct:g} % = "
                             f"{wl_p90 * pct / 100:.0f}")
        newn = new_numbers(lead, known)
        if nl_p90 is not None and len(newn) > nl_p90:
            rep.fail("IT11", f"{vid}: {len(newn)} new numbers in the lead ({', '.join(newn)}); CE numbers_lead p90 = {nl_p90:g}")
        # IT9 cue scan (advisory → V11)
        if b is not None:
            k = b["knobs"]
            for kind, knob, free in (("route", "route", "zelf vinden"), ("direction", "direction", "open")):
                if k.get(knob) != free:
                    continue
                for where, t in (("lead", lead), ("task", task)):
                    for h in cue_hits(t, cues, kind):
                        measured["cues"].append({"vraag_id": vid, "knob": knob, "where": where, "phrase": h})
                        rep.warn("IT9", f"{vid}: {knob} planned '{free}' but the {where} says '{h}'")
    if any(b and b["knobs"].get("route") == "zelf vinden" for b in bv.values()):
        for h in cue_hits(it.get("intro") or "", cues, "route"):
            measured["cues"].append({"vraag_id": None, "knob": "route", "where": "intro", "phrase": h})
            rep.warn("IT9", f"{oid}: the intro gives a route ('{h}') while a vraag plans 'zelf vinden'")
    # IT10 term giveaway
    concepts = concept_index(run.criteria_doc, glossary)
    used = {s["criterion_id"] for v in it["vragen"] for s in v["cv"]["scorepunten"]}
    if not any(concepts.get(c) for c in used):
        rep.info("IT10", f"{oid}: the criteria of this opgave have no concepts and no glossary term: term giveaway not "
                         f"checked (advisory only)")
    for h in giveaways(it, bv, concepts, rules, cues):
        measured["giveaways"].append(h)
        msg = (f"{h['vraag_id']} s{h['seq']}: '{h['concept']}' stands in the {'/'.join(h['where'])} while scorepunt "
               f"{h['seq']} ({h['bloom']}) asks for it (term giveaway)")
        (rep.fail if h["severity"] == "fail" else rep.warn)("IT10", msg)
    # RB reading budget
    pts = sum(v["points"] for v in it["vragen"])
    lim = budget(pts, hr, pct)
    w = measured["words"]["total"]
    if lim is not None and w > lim:
        rep.fail("RB", f"{oid}: {w} words (intro {measured['words']['intro']}, sources {measured['words']['sources']}, "
                       f"leads {measured['words']['leads']}, tasks {measured['words']['tasks']}) > budget {lim:.0f} "
                       f"({pts} p × {hr['words_per_point']['pooled']:g} × {pct:g} % × 1,1)")
    bp_ids = [o["opgave_id"] for o in run.blueprint()["opgaven"]]
    if lim is not None and all(x in all_items for x in bp_ids):
        tot_w = sum(opgave_words(all_items[x])["total"] for x in bp_ids)
        tot_p = sum(v["points"] for x in bp_ids for v in all_items[x]["vragen"])
        tl = budget(tot_p, hr, pct)
        if tot_w > tl:
            rep.fail("RB", f"toets: {tot_w} words > budget {tl:.0f} ({tot_p} p × {hr['words_per_point']['pooled']:g} × "
                           f"{pct:g} % × 1,1)")
    return measured


def budget_lines(run) -> list[str]:
    """Per opgave the limits a writer gets in its prompt (specs/36 §5.4, §6 RB/IT8/IT11)."""
    hr, pct = run.house, run.order.get("reading_budget_pct")
    if not hr:
        return ["geen huisregels gemeten: no reading budget or lead/task limits"]
    out = []
    wt = hr["words_task"]["p90"]
    wl = hr["words_lead"]["p90"] * pct / 100 if pct is not None else None
    nl90 = hr["numbers_lead"]["p90"]
    for o in run.blueprint()["opgaven"]:
        if o.get("reused_from"):
            continue
        p = sum(v["points"] for v in o["vragen"])
        b = budget(p, hr, pct)
        out.append(f"{o['opgave_id']}: {p} p; reading budget " + (f"≤ {b:.0f} words (intro + sources + leads + tasks)" if b else
                   "none (reading_budget_pct null)") + (f"; lead ≤ {wl:.0f} words" if wl is not None else "")
                   + f" and ≤ {nl90:g} new numbers; task ≤ {wt:g} words")
    return out


if __name__ == "__main__":
    import sys
    from toetsrun import ToetsRun, subjects_opt
    if len(sys.argv) < 3 or sys.argv[2] != "--budget":
        print("Usage: house_checks.py <run_dir> --budget [--subjects <dir>]   (the writers' limits per opgave)")
        sys.exit(2)
    for line in budget_lines(ToetsRun(Path(sys.argv[1]), subjects_opt(sys.argv))):
        print(line)
