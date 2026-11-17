"""The central-exam house rules (specs/36 §3.1): computed from B/metrics/<exam_id>.json by profile_build.py into the
`house_rules` block of referentieprofiel.json and the section *Huisregels eindexamen* of referentieprofiel.md.

| key                | definition                                                                                         |
|--------------------|----------------------------------------------------------------------------------------------------|
| minutes_per_point  | duration / max_score, pooled over the exams with a known duration                                   |
| words_per_point    | (intro + sources + leads + tasks) / points: pooled, and p25/p50/p75 over opgaven                      |
| points_per_opgave  | mean, min, max          · vragen_per_opgave: mean, min, max                                          |
| groups_per_point   | distinct groups / points per exam: pooled and max over exams · groups_per_opgave: mean, max         |
| words_task         | p50, p90 over vragen    · words_lead: p50, p90, share of vragen with an empty lead                   |
| numbers_lead       | p50, p90 over vragen                                                                                |
| n_tasks            | per pattern: share of vragen with 1, 2, 3+ tasks; max_tasks = the highest value seen on ≥ 10 % of    |
|                    | that pattern's vragen (else 1); a '+'-combination counts for each of its codes                      |
Patterns come from the bank's current labels (labels/<exam_id>.json), else from the metrics file.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "toets"))
from ecommon import load_json  # noqa: E402
from tcommon import exam_label, pattern_codes  # noqa: E402

MAX_TASKS_SHARE = 0.10


def pctl(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (pos - lo), 1)


def stat3(xs: list[float]) -> dict:
    return {"mean": round(sum(xs) / len(xs), 2) if xs else 0.0, "min": min(xs) if xs else 0, "max": max(xs) if xs else 0}


def opgave_words(o: dict, vragen: list[dict]) -> int:
    return o["words_intro"] + o["words_sources"] + sum(v["words_lead"] + v["words_task"] for v in vragen)


def load_metrics(bank: Path, reg: dict) -> list[dict]:
    out = []
    for e in reg.get("exams", []):
        p = bank / "metrics" / f"{e['exam_id']}.json"
        if p.exists():
            out.append(load_json(p))
    return out


def compute(bank: Path, reg: dict) -> dict | None:
    metrics = load_metrics(bank, reg)
    if not metrics:
        return None
    wpp_op, ppo, vpo, gpo = [], [], [], []
    w_task, w_lead, n_lead = [], [], []
    per_exam = []
    tot_words = tot_points = 0
    dur_sum = dur_pts = 0
    g_sum = g_pts = 0
    gpp = []
    tasks = defaultdict(list)
    for m in metrics:
        eid = m["exam_id"]
        labp = bank / "labels" / f"{eid}.json"
        lab_pat = {q["question_id"]: q.get("pattern") for q in load_json(labp)["questions"]} if labp.exists() else {}
        e_words = e_points = 0
        for o in m["opgaven"]:
            vs = [v for v in m["vragen"] if v["opgave_id"] == o["opgave_id"]]
            w = opgave_words(o, vs)
            e_words += w
            e_points += o["points"]
            if o["points"]:
                wpp_op.append(w / o["points"])
            ppo.append(o["points"])
            vpo.append(o["n_vragen"])
            gpo.append(o["n_groups"])
        for v in m["vragen"]:
            w_task.append(v["words_task"])
            w_lead.append(v["words_lead"])
            n_lead.append(v["numbers_lead"])
            pat = lab_pat.get(v["question_id"], v.get("pattern"))
            for c in pattern_codes(pat):
                if c != "NIEUW":
                    tasks[c].append(max(1, v["n_tasks"]))
        tot_words += e_words
        tot_points += e_points
        mpp = None
        if m.get("duration_minutes") and m.get("max_score"):
            dur_sum += m["duration_minutes"]
            dur_pts += m["max_score"]
            mpp = round(m["duration_minutes"] / m["max_score"], 2)
        eg = None
        if m.get("n_groups") and e_points:
            g_sum += m["n_groups"]
            g_pts += e_points
            eg = round(m["n_groups"] / e_points, 3)
            gpp.append(eg)
        per_exam.append({"exam_id": eid, "duration_minutes": m.get("duration_minutes"), "max_score": m.get("max_score"),
                         "minutes_per_point": mpp, "words": e_words,
                         "words_per_point": round(e_words / e_points, 1) if e_points else None,
                         "n_opgaven": m["n_opgaven"], "points_per_opgave": stat3([o["points"] for o in m["opgaven"]]),
                         "groups_per_point": eg})
    n_tasks = {}
    for code, ns in sorted(tasks.items()):
        c = Counter(ns)
        shares = {"1": round(c[1] / len(ns), 3), "2": round(c[2] / len(ns), 3),
                  "3+": round(sum(n for k, n in c.items() if k >= 3) / len(ns), 3)}
        seen = [k for k, n in c.items() if n / len(ns) >= MAX_TASKS_SHARE]
        n_tasks[code] = {"n_vragen": len(ns), "shares": shares, "max_tasks": max(seen) if seen else 1}
    hr = {"source": "bank-metrics",
          "label": f"huisregels: {len(metrics)} examen{'s' if len(metrics) != 1 else ''} "
                   f"({', '.join(exam_label(m['exam_id']) for m in metrics)})",
          "n_exams": len(metrics), "exams": [m["exam_id"] for m in metrics],
          "minutes_per_point": round(dur_sum / dur_pts, 2) if dur_pts else None,
          "words_per_point": {"pooled": round(tot_words / tot_points, 1) if tot_points else 0.0,
                              "p25": pctl(wpp_op, 0.25), "p50": pctl(wpp_op, 0.5), "p75": pctl(wpp_op, 0.75)},
          "points_per_opgave": stat3(ppo), "vragen_per_opgave": stat3(vpo),
          "groups_per_point": {"pooled": round(g_sum / g_pts, 3) if g_pts else None, "max": max(gpp) if gpp else None},
          "groups_per_opgave": {"mean": round(sum(gpo) / len(gpo), 2) if gpo and any(gpo) else None,
                                "max": max(gpo) if gpo and any(gpo) else None},
          "words_task": {"p50": pctl(w_task, 0.5), "p90": pctl(w_task, 0.9)},
          "words_lead": {"p50": pctl(w_lead, 0.5), "p90": pctl(w_lead, 0.9),
                         "empty_share": round(sum(1 for x in w_lead if x == 0) / len(w_lead), 3) if w_lead else 0.0},
          "numbers_lead": {"p50": pctl(n_lead, 0.5), "p90": pctl(n_lead, 0.9)},
          "n_tasks": n_tasks, "per_exam": per_exam}
    return hr


def nl(x, d: int = 1) -> str:
    if x is None:
        return "–"
    if isinstance(x, float) and x != int(x):
        return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{int(x):,}".replace(",", ".")


def render_md(hr: dict | None) -> list[str]:
    L = ["## Huisregels eindexamen", ""]
    if not hr:
        return L + ["Geen huisregels gemeten (draai `scripts/exam/exam_metrics.py <vak>`).", ""]
    L += [f"*{hr.get('label') or hr['source']}* — gemeten met `scripts/exam/exam_metrics.py` (specs/36 §3).", "",
          "| regel | eindexamen |", "|---|---|",
          f"| minuten per punt | {nl(hr['minutes_per_point'], 2)} |",
          f"| woorden per punt (alle opgaven) | {nl(hr['words_per_point']['pooled'])} (per opgave p25 {nl(hr['words_per_point']['p25'])}, "
          f"p50 {nl(hr['words_per_point']['p50'])}, p75 {nl(hr['words_per_point']['p75'])}) |",
          f"| punten per opgave | gem. {nl(hr['points_per_opgave']['mean'])} (min {nl(hr['points_per_opgave']['min'])}, "
          f"max {nl(hr['points_per_opgave']['max'])}) |",
          f"| vragen per opgave | gem. {nl(hr['vragen_per_opgave']['mean'])} (min {nl(hr['vragen_per_opgave']['min'])}, "
          f"max {nl(hr['vragen_per_opgave']['max'])}) |",
          f"| leerdoelen per punt | {nl(hr['groups_per_point']['pooled'], 3)} (max per examen {nl(hr['groups_per_point']['max'], 3)}) |",
          f"| leerdoelen per opgave | gem. {nl(hr['groups_per_opgave']['mean'])} (max {nl(hr['groups_per_opgave']['max'])}) |",
          f"| woorden in de taak | p50 {nl(hr['words_task']['p50'])}, p90 {nl(hr['words_task']['p90'])} |",
          f"| woorden in de lead | p50 {nl(hr['words_lead']['p50'])}, p90 {nl(hr['words_lead']['p90'])}; "
          f"{round(hr['words_lead']['empty_share'] * 100)} % van de vragen zonder lead |",
          f"| nieuwe getallen in de lead | p50 {nl(hr['numbers_lead']['p50'])}, p90 {nl(hr['numbers_lead']['p90'])} |", ""]
    if hr.get("n_tasks"):
        L += ["**Taken per vraag** (aandeel vragen met 1, 2, 3+ taken; max_tasks = hoogste waarde op ≥ 10 % van de vragen)", "",
              "| patroon | vragen | 1 | 2 | 3+ | max_tasks |", "|---|---|---|---|---|---|"]
        for c, d in hr["n_tasks"].items():
            s = d["shares"]
            L.append(f"| {c} | {d['n_vragen']} | {round(s['1'] * 100)} % | {round(s['2'] * 100)} % | {round(s['3+'] * 100)} % | {d['max_tasks']} |")
        L.append("")
    if hr.get("per_exam"):
        L += ["**Per examen**", "", "| examen | duur | max. score | min/punt | woorden | woorden/punt | opgaven | punten/opgave | leerdoelen/punt |",
              "|---|---|---|---|---|---|---|---|---|"]
        for e in hr["per_exam"]:
            L.append(f"| {exam_label(e['exam_id'])} | {nl(e['duration_minutes'])} | {nl(e['max_score'])} | {nl(e['minutes_per_point'], 2)} | "
                     f"{nl(e['words'])} | {nl(e['words_per_point'])} | {e['n_opgaven']} | {nl(e['points_per_opgave']['mean'])} | "
                     f"{nl(e['groups_per_point'], 3)} |")
        L.append("")
    return L
