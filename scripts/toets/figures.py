#!/usr/bin/env python3
"""T3 — render the figures of an opgave from the writer's specs and check their numbers (specs/35 §3, specs/34 FG).

Usage: figures.py <run_dir> --opgave <id> [--subjects <dir>] [--no-render]

Types rendered with matplotlib (black and grey, 200 dpi, 14 cm wide): market_model, line_chart, bar_chart.
game_matrix (and simple tables) are Word tables, not images: checked, not rendered. Other types (flow) are reported
as not built. Every coordinate in `spec` and `answer_spec` (line points, points, area corners, bar values) must be a
`data` value or a calc result of the opgave (0 and the axis limits are allowed); an answer element that names a
`calc` must sit exactly on that calc's value (e.g. the equilibrium price). A source or blueprint vraag that refers
to a figure id needs that figure. Writes figures/<id>.png (student) and figures/<id>-cv.png (with the answer_spec).
"""
from __future__ import annotations

import sys
from pathlib import Path

from calc_check import evaluate
from nlnum import close
from tcommon import Report, load_json
from toetsrun import ToetsRun, opt, subjects_opt

RENDERED = {"market_model", "line_chart", "bar_chart"}
TABLES = {"game_matrix"}


def coords(spec: dict) -> list[tuple[str, float]]:
    out = []
    for ln in spec.get("lines", []):
        for p in ln.get("points", []):
            out += [(f"line '{ln.get('label')}'", float(x)) for x in p]
    for p in spec.get("points", []):
        out += [(f"point '{p.get('label')}'", float(x)) for x in p.get("xy", [])]
    for a in spec.get("areas", []):
        for p in a.get("polygon", []):
            out += [(f"area '{a.get('label')}'", float(x)) for x in p]
    for b in spec.get("bars", []):
        out.append((f"bar '{b.get('label')}'", float(b.get("value"))))
    return out


def calc_refs(spec: dict) -> list[tuple[str, str, list[float]]]:
    """Elements of an answer_spec that name a calc: (label, calc name, their coordinates)."""
    out = []
    for p in spec.get("points", []):
        for key, idx in (("calc_x", 0), ("calc_y", 1), ("calc", 1)):
            if p.get(key):
                out.append((f"point '{p.get('label')}'", p[key], [float(p["xy"][idx])]))
    for ln in spec.get("lines", []):
        if ln.get("calc"):
            out.append((f"line '{ln.get('label')}'", ln["calc"], [float(q[1]) for q in ln.get("points", [])]))
    return out


def render(spec: dict, answer: dict | None, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 4.0))
    greys = ["black", "dimgray", "gray", "darkgray"]
    if spec["type"] == "bar_chart":
        bars = spec.get("bars", [])
        ax.bar([b["label"] for b in bars], [b["value"] for b in bars], color="lightgray", edgecolor="black")
    for i, ln in enumerate(spec.get("lines", [])):
        xs, ys = zip(*ln["points"])
        ax.plot(xs, ys, color=greys[i % len(greys)], linewidth=1.5)
        ax.annotate(ln.get("label", ""), (xs[-1], ys[-1]), textcoords="offset points", xytext=(4, 2), fontsize=8)
    for p in spec.get("points", []):
        ax.plot(*p["xy"], "o", color="black", markersize=3)
    for a in spec.get("areas", []):
        ax.fill(*zip(*a["polygon"]), fill=False, hatch="///", edgecolor="gray")
    if answer:
        if answer.get("bars"):
            ax.bar([b["label"] for b in answer["bars"]], [b["value"] for b in answer["bars"]], color="white",
                   edgecolor="black", hatch="///")
        for ln in answer.get("lines", []):
            xs, ys = zip(*ln["points"])
            ax.plot(xs, ys, color="black", linestyle="--", linewidth=1.5)
            ax.annotate(ln.get("label", ""), (xs[-1], ys[-1]), textcoords="offset points", xytext=(4, 2), fontsize=8)
        for p in answer.get("points", []):
            ax.plot(*p["xy"], "o", color="black", markersize=4)
            ax.annotate(p.get("label", ""), p["xy"], textcoords="offset points", xytext=(4, 4), fontsize=8)
        for a in answer.get("areas", []):
            ax.fill(*zip(*a["polygon"]), fill=False, hatch="xxx", edgecolor="black")
    for axis, setter_l, setter_lim in (("x", ax.set_xlabel, ax.set_xlim), ("y", ax.set_ylabel, ax.set_ylim)):
        a = spec.get(axis) or {}
        if a.get("label"):
            setter_l(a["label"])
        if a.get("min") is not None and a.get("max") is not None:
            setter_lim(a["min"], a["max"])
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=10)
    if spec.get("grid"):
        ax.grid(True, color="lightgray", linewidth=0.5)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main(argv: list[str]) -> None:
    if len(argv) < 2 or not opt(argv, "--opgave"):
        print(__doc__)
        sys.exit(2)
    R, oid = Path(argv[1]), opt(argv, "--opgave")
    rep = Report(f"figures {oid}")
    run = ToetsRun(R, subjects_opt(argv))
    it = load_json(R / "33_items" / f"{oid}.json")
    vals, errs = evaluate(it)
    allowed = [0.0] + list(it["data"].values()) + [v["value"] for v in vals.values()] + [v["raw"] for v in vals.values()]
    figs = {f["figure_id"]: f for f in it["figures"]}
    for s in it["sources"]:
        if s.get("figure_id") and s["figure_id"] not in figs:
            rep.fail("FG", f"informatiebron {s['n']} refers to figure {s['figure_id']}, which is not in figures")
    og = next((o for o in run.blueprint()["opgaven"] if o["opgave_id"] == oid), {"vragen": []})
    for v in og["vragen"]:
        if v.get("figure") and v["figure"] not in figs:
            rep.fail("FG", f"{v['vraag_id']}: the blueprint plans figure {v['figure']}, the items have none")
    for fid, f in figs.items():
        spec, ans = f["spec"], f.get("answer_spec") or {}
        typ = spec.get("type")
        axes = [float(spec.get(a, {}).get(k)) for a in ("x", "y") for k in ("min", "max") if spec.get(a, {}).get(k) is not None]
        for where, sp in (("spec", spec), ("answer_spec", ans)):
            for label, x in coords(sp):
                if not any(close(x, a) for a in allowed + axes):
                    rep.fail("FG", f"{fid} {where} {label}: coordinate {x:g} is not a data value or a calc result")
        for label, name, xs in calc_refs(ans):
            if name not in vals:
                rep.fail("FG", f"{fid} answer_spec {label}: calc '{name}' does not exist")
            elif not all(close(x, vals[name]["value"]) for x in xs):
                rep.fail("FG", f"{fid} answer_spec {label}: {xs} contradicts calc {name} = {vals[name]['value']:g}")
        if typ in TABLES:
            rep.info("FG", f"{fid}: {typ} becomes a Word table, not an image")
            continue
        if typ not in RENDERED:
            rep.warn("FG", f"{fid}: figure type '{typ}' is not built yet (rendered types: {', '.join(sorted(RENDERED))})")
            continue
        if "--no-render" not in argv and not rep.failed:
            render(spec, None, R / "figures" / f"{fid}.png")
            render(spec, ans, R / "figures" / f"{fid}-cv.png")
            rep.info("FG", f"{fid}: rendered figures/{fid}.png and {fid}-cv.png")
    if not figs:
        rep.info("FG", f"{oid}: no figures")
    rep.print_and_exit(str(R / "33_checks" / f"{oid}.figures.json"))


if __name__ == "__main__":
    main(sys.argv)
