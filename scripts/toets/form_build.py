#!/usr/bin/env python3
"""T0 / `/toets --formulier <subject>` — build the local order form (specs/32 §2).

Usage: form_build.py <subject> [--bank <dir>] [--toetsbank <dir>] [--subjects <dir>] [--base <file>] [--knobs <file>]
                     [--out <file>]

Writes one self-contained HTML file (default subjects/<s>/toets/toetsformulier-<s>.html, git-ignored): Dutch UI, no
network, works from file://. Embedded as JSON in <script type="application/json" id="toets-data">:
  - the leerdoelen and criteria of the bank's criteria version (id, student text, Bloom, domein → subdomein);
  - the reference profile (profiel/referentieprofiel.json, else the seed, labelled "voorlopig", else none), per knob
    value pooled and per exam;
  - the Bloom mix of the bank's linked points (pooled and per exam);
  - the catalogue (base + subject; code, name, kind, Bloom list, in_central_exam) and the knob definitions;
  - the context history (last 20 of toetsbank/contexts.json), the toetsbank opgaven for reuse and the templates
    (toets/sjablonen/*.json).
The teacher downloads toetsopdracht.json (and optionally a template); `validate_toets.py order` does the full check.
A knob the teacher leaves "niet ingesteld" is left out of the file and asked in /toets (no implicit default).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from tcommon import (BASE_PATTERNS_PATH, KNOBS_PATH, MIX_LEVELS, ROOT, clean_reference, exam_label, knob_index, load_json,
                     merged_catalogue)


def opt(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None


def ancestors(units: dict, uid: str) -> dict:
    out, cur, seen = {}, units.get(uid), set()
    while cur is not None and cur["unit_id"] not in seen:
        seen.add(cur["unit_id"])
        if cur.get("kind") in ("domein", "subdomein"):
            out.setdefault(cur["kind"], {"code": cur.get("code") or cur["unit_id"], "title": cur.get("title") or ""})
        cur = units.get(cur.get("parent_id")) if cur.get("parent_id") else None
    return out


def reference_code(ref: dict) -> str:
    if ref["source"] == "bank-labels":
        return f"bank-{ref['n_exams']}-examens"
    return ref["source"]


def build_data(subject: str, argv: list[str]) -> dict:
    subjects = Path(opt(argv, "--subjects")) if opt(argv, "--subjects") else ROOT / "subjects"
    bank = Path(opt(argv, "--bank")) if opt(argv, "--bank") else subjects / subject / "examenbank"
    tbank = Path(opt(argv, "--toetsbank")) if opt(argv, "--toetsbank") else subjects / subject / "toetsbank"
    if not (bank / "criteria.json").exists() or not (bank / "register.json").exists():
        sys.exit(f"[form_build] no exam bank with criteria at {bank}: the toets-straat needs a criteria version (specs/30 §2)")
    reg = load_json(bank / "register.json")
    units = {u["unit_id"]: u for u in load_json(bank / "source_units.json")["units"]} if (bank / "source_units.json").exists() else {}
    groups = []
    for g in load_json(bank / "criteria.json")["groups"]:
        anc = ancestors(units, g["unit_id"])
        groups.append({"group_id": g["group_id"], "unit_id": g["unit_id"],
                       "domein": anc.get("domein", {"code": "?", "title": ""}),
                       "subdomein": anc.get("subdomein", {"code": "?", "title": ""}),
                       "goal": g["goal"].get("text_student") or g["goal"]["text_expert"], "goal_bloom": g["goal"].get("bloom"),
                       "criteria": [{"criterion_id": c["criterion_id"], "text": c.get("text_student") or c["text_expert"],
                                     "bloom": c["bloom"]} for c in g["criteria"]]})
    # reference profile
    rp = bank / "profiel" / "referentieprofiel.json"
    seed = subjects / subject / "toets" / "seed_profile.json"
    if rp.exists():
        ref = load_json(rp)
    elif seed.exists():
        ref = load_json(seed)
        ref.setdefault("label", "referentie: voorlopig (seed)")
    else:
        ref = {"source": "none", "label": "referentie: geen", "n_exams": 0, "pooled": {}, "exams": [],
               "unknown_knobs": [], "points": 0}
    ref = clean_reference(ref, knob_index(load_json(opt(argv, "--knobs") or KNOBS_PATH))) or ref
    stale = ref.get("stale_knobs") or []
    reference = {"code": reference_code(ref), "stale_knobs": stale, "label": (ref.get("label") or ref["source"]) + (f" (verouderd voor {', '.join(stale)}: examens opnieuw labelen)" if stale else ""), "source": ref["source"],
                 "provisional": ref["source"] != "bank-labels", "unknown_knobs": ref.get("unknown_knobs", []),
                 "pooled": {k: {v: d["share"] for v, d in vals.items()} for k, vals in (ref.get("pooled") or {}).items()},
                 "exams": [{"exam_id": e["exam_id"], "label": exam_label(e["exam_id"]),
                            "shares": {k: ({v: p / sum(vals.values()) for v, p in vals.items()} if sum(vals.values()) else {})
                                       for k, vals in e["knobs"].items()}} for e in ref.get("exams", [])]}
    # Bloom mix of linked points in the bank
    bl_pool, bl_exam = defaultdict(float), {}
    for e in reg["exams"]:
        lp = bank / "links" / f"{e['exam_id']}.json"
        if not lp.exists():
            continue
        per = defaultdict(float)
        for sp in load_json(lp)["scorepunten"]:
            if sp.get("criterion_id") and sp.get("bloom"):
                per[sp["bloom"]] += sp["points"]
        tot = sum(per.values())
        if tot:
            bl_exam[exam_label(e["exam_id"])] = {k: v / tot for k, v in per.items()}
            for k, v in per.items():
                bl_pool[k] += v
    tot = sum(bl_pool.values())
    exam_bloom = {"pooled": {k: v / tot for k, v in bl_pool.items()} if tot else {}, "exams": bl_exam,
                  "n_exams": len(bl_exam)}
    # catalogue and knobs
    cat = merged_catalogue(subject, Path(opt(argv, "--base") or BASE_PATTERNS_PATH), subjects)
    catalogue = [{"code": p["code"], "name": p["name"], "kind": p["kind"], "bloom": p["bloom"], "layer": p["layer"],
                  "in_central_exam": p["in_central_exam"], "knobs_fixed": p["knobs_fixed"]}
                 for p in cat["patterns"] if p.get("status") == "active"]
    knobs = [k for k in load_json(opt(argv, "--knobs") or KNOBS_PATH)["knobs"]]
    # toetsbank: history, reuse
    contexts, reuse = [], []
    if (tbank / "contexts.json").exists():
        contexts = sorted(load_json(tbank / "contexts.json")["contexts"], key=lambda c: c["date"], reverse=True)[:20]
    if (tbank / "register.json").exists():
        treg = load_json(tbank / "register.json")
        if treg["criteria_run"] == reg["criteria_run"]:
            for t in treg["toetsen"]:
                tf = tbank / "toetsen" / f"{t['toets_id']}.json"
                if not tf.exists():
                    continue
                for og in load_json(tf)["opgaven"]:
                    pts = defaultdict(int)
                    for v in og["vragen"]:
                        for s in v["scorepunten"]:
                            pts[s.get("group_id") or "?"] += s["points"]
                    reuse.append({"toets_id": t["toets_id"], "toets_title": t["title"], "opgave_id": og["opgave_id"],
                                  "title": og["title"], "points": sum(pts.values()), "groups": dict(pts)})
    templates = []
    sj = subjects / subject / "toets" / "sjablonen"
    if sj.exists():
        for f in sorted(sj.glob("*.json")):
            templates.append({"name": f.stem, "data": load_json(f)})
    return {"subject": subject, "criteria_run": reg["criteria_run"], "groups": groups, "reference": reference,
            "exam_bloom": exam_bloom, "catalogue": catalogue, "knobs": knobs, "mix_levels": MIX_LEVELS,
            "levels": ["4vwo", "5vwo", "6vwo"], "contexts": contexts, "reuse": reuse, "templates": templates}


def render(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=None).replace("</", "<\\/")
    return TEMPLATE.replace("__SUBJECT__", data["subject"]).replace("__DATA__", payload)


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[1].startswith("--"):
        print(__doc__)
        sys.exit(2)
    subject = argv[1]
    data = build_data(subject, argv)
    subjects = Path(opt(argv, "--subjects")) if opt(argv, "--subjects") else ROOT / "subjects"
    out = Path(opt(argv, "--out") or subjects / subject / "toets" / f"toetsformulier-{subject}.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data), encoding="utf-8")
    print(f"[form_build] {subject}: {len(data['groups'])} leerdoelen, {len(data['catalogue'])} patronen, "
          f"{data['reference']['label']} -> {out}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Toetsopdracht — __SUBJECT__</title>
<style>
  :root { --fg:#1d1d1f; --muted:#6b6b70; --line:#d9d9de; --bg:#fafafa; --accent:#1f5fa8; --warn:#a14a00; --ok:#2f6b2f; }
  * { box-sizing: border-box; }
  body { font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Arial, sans-serif; color: var(--fg); background: var(--bg);
         margin: 0; padding: 0 0 4rem; }
  header { background: #fff; border-bottom: 1px solid var(--line); padding: 1rem 1.5rem; position: sticky; top: 0; z-index: 2; }
  header h1 { margin: 0; font-size: 1.25rem; }
  header .sum { color: var(--muted); margin-top: .25rem; }
  main { max-width: 1100px; margin: 0 auto; padding: 1rem 1.5rem; }
  section { background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 1rem 1.25rem; margin: 1rem 0; }
  h2 { font-size: 1.05rem; margin: 0 0 .75rem; }
  h3 { font-size: .95rem; margin: 1rem 0 .4rem; }
  h4 { font-size: .9rem; margin: .6rem 0 .3rem; color: var(--muted); font-weight: 600; }
  label { display: inline-flex; gap: .4rem; align-items: center; margin-right: 1rem; }
  input[type=number] { width: 5rem; }
  input[type=text] { width: 22rem; max-width: 100%; }
  textarea { width: 100%; min-height: 3rem; }
  button { font: inherit; border: 1px solid var(--line); background: #fff; border-radius: 6px; padding: .25rem .6rem; cursor: pointer; }
  button.on { background: var(--accent); color: #fff; border-color: var(--accent); }
  button.primary { background: var(--accent); color: #fff; border-color: var(--accent); padding: .45rem 1rem; }
  button:disabled { opacity: .45; cursor: default; }
  .muted { color: var(--muted); }
  .ref { color: var(--muted); font-size: .85em; }
  .note { color: var(--muted); font-style: italic; font-size: .85em; }
  .warn { color: var(--warn); }
  .ok { color: var(--ok); }
  table { border-collapse: collapse; width: 100%; }
  td, th { border-bottom: 1px solid var(--line); padding: .3rem .4rem; text-align: left; vertical-align: top; }
  th { font-weight: 600; font-size: .85em; color: var(--muted); }
  .grow { width: 100%; }
  .knob { border-top: 1px solid var(--line); padding: .6rem 0; }
  .knob .head { display: flex; gap: .5rem; align-items: baseline; flex-wrap: wrap; }
  .knob .head b { min-width: 11rem; }
  .vals { margin: .3rem 0 0 1rem; }
  .vals .row { display: grid; grid-template-columns: 16rem 10rem 4.5rem 1fr; gap: .5rem; align-items: center; margin: .15rem 0; }
  .state { font-size: .85em; padding: .05rem .4rem; border-radius: 4px; background: #eee; }
  details summary { cursor: pointer; color: var(--accent); font-size: .85em; }
  ul.crit { margin: .3rem 0 .3rem 1rem; padding: 0; list-style: none; }
  ul.crit li { margin: .15rem 0; }
  #messages li { margin: .15rem 0; }
  #selftest { display: none; }
</style>
</head>
<body>
<header>
  <h1>Toetsopdracht — <span id="subj"></span></h1>
  <div class="sum" id="topsum"></div>
</header>
<main>
<section id="s-toets">
  <h2>1. Toets</h2>
  <p><label>Titel <input type="text" id="title" placeholder="bijv. Toets F2 Kosten en winst"></label></p>
  <p>Niveau <span id="levels"></span> <span class="note">Het niveau zet geen knoppen; het stuurt taal, context en getallen.</span></p>
  <p>
    <label>Aantal opgaven <input type="number" id="n_opgaven" min="1" step="1"></label>
    <label>Aantal vragen <input type="number" id="n_vragen" min="1" step="1"></label>
    <label>Tijdsduur (min) <input type="number" id="duration" min="1" step="5"></label>
  </p>
  <p><label>Sjabloon laden <select id="tplsel"><option value="">—</option></select></label>
     <label>of bestand <input type="file" id="tplfile" accept=".json,application/json"></label></p>
</section>

<section id="s-matrix">
  <h2>2. Toetsmatrijs <span class="muted" id="mtotal"></span></h2>
  <p class="note">Punten per leerdoel. Klap een leerdoel open om criteria uit te sluiten. Leerdoelen zonder punten doen niet mee.</p>
  <div id="matrix"></div>
</section>

<section id="s-bloom">
  <h2>3. Bloom-mix (optioneel)</h2>
  <p id="bloommode"></p>
  <div id="bloom"></div>
</section>

<section id="s-knobs">
  <h2>4. Knoppen</h2>
  <p class="note">Aandelen zijn per punt. In grijs: het aandeel in het centraal examen (<span id="reflabel"></span>).
     Een knop die <i>niet ingesteld</i> blijft, vraagt /toets je straks.</p>
  <div id="knobs"></div>
</section>

<section id="s-context">
  <h2>5. Contexten</h2>
  <div id="ctxfixed"></div>
  <p><label class="grow">Ook vermijden (komma of nieuwe regel) <textarea id="avoid"></textarea></label></p>
  <h4>Eerdere contexten (worden altijd vermeden)</h4>
  <div id="history"></div>
</section>

<section id="s-reuse">
  <h2>6. Hergebruik uit de toetsbank</h2>
  <div id="reuse"></div>
</section>

<section id="s-download">
  <h2>7. Downloaden</h2>
  <ul id="messages"></ul>
  <p><button class="primary" id="dl">Download toetsopdracht.json</button>
     <label>Sjabloonnaam <input type="text" id="tplname" placeholder="mijn-5vwo-toets" style="width:14rem"></label>
     <button id="dltpl">Opslaan als sjabloon</button>
     <button id="clear">Concept wissen</button></p>
  <p class="note">Zet het bestand daarna in /toets: <code>/toets toetsopdracht.json --subject <span class="subj2"></span></code>.
     De volledige controle gebeurt daar (<code>validate_toets.py order</code>).</p>
</section>
<pre id="selftest"></pre>
</main>

<script type="application/json" id="toets-data">__DATA__</script>
<script>
"use strict";
const D = JSON.parse(document.getElementById("toets-data").textContent);
const KNOBS = D.knobs.filter(k => k.settable);
const COMPUTED = D.knobs.filter(k => !k.settable);
const APPLIES_NOTE = {route: "telt alleen over reken- en schemavragen", schema: "telt alleen over schemavragen",
                      builds_on: "telt niet over de eerste vraag van een opgave"};
const LEVEL_NL = {"4vwo": "4 VWO", "5vwo": "5 VWO", "6vwo": "6 VWO"};
const S = {title: "", level: null, n_opgaven: null, n_vragen: null, duration: null, points: {}, exclude: {},
           bloomMode: "ask", bloom: {}, knobs: {}, contexts: {}, avoid: "", reuse: {}, template: null};
const STORE = "toetsformulier-" + D.subject;

function el(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") e.className = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined && v !== false) e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined) e.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return e;
}
const pct = x => (Math.round(x * 1000) / 10).toString().replace(".", ",") + " %";
function valuesOf(k) { return k.values === "catalogue" ? D.catalogue.map(p => p.code) : k.values; }
function valueLabel(k, v) {
  if (k.values !== "catalogue") return v;
  const p = D.catalogue.find(p => p.code === v);
  return p ? v + " " + p.name + (p.in_central_exam ? "" : " (niet in centraal examen)") : v;
}
function total() { return Object.values(S.points).reduce((a, b) => a + (b || 0), 0); }
function save() { try { localStorage.setItem(STORE, JSON.stringify(S)); } catch (e) { /* no storage from file:// is fine */ } }
function load() { try { const s = JSON.parse(localStorage.getItem(STORE) || "null"); if (s) Object.assign(S, s); } catch (e) { } }

function refFor(knobId) {
  const R = D.reference;
  if (knobId === "bloom") {
    if (Object.keys(D.exam_bloom.pooled).length) return {pooled: D.exam_bloom.pooled, exams: D.exam_bloom.exams};
  }
  if (R.unknown_knobs.includes(knobId) || !R.pooled[knobId]) return null;
  const exams = {};
  for (const e of R.exams) if (e.shares[knobId]) exams[e.label] = e.shares[knobId];
  return {pooled: R.pooled[knobId], exams};
}
function refText(ref, v) {
  if (!ref) return "eindexamen: onbekend";
  let t = "eindexamen: " + pct(ref.pooled[v] || 0);
  const ex = Object.entries(ref.exams || {});
  if (ex.length > 1) t += ", " + ex.map(([lab, sh]) => lab + " " + pct(sh[v] || 0)).join(", ");
  return t;
}
function roundTo100(shares, values) {   // largest remainder to whole percentages summing to 100
  const raw = values.map(v => (shares[v] || 0) * 100), sum = raw.reduce((a, b) => a + b, 0);
  if (!sum) return null;
  const scaled = raw.map(x => x * 100 / sum), fl = scaled.map(Math.floor);
  let rest = 100 - fl.reduce((a, b) => a + b, 0);
  scaled.map((x, i) => [x - fl[i], i]).sort((a, b) => b[0] - a[0]).forEach(([_, i]) => { if (rest > 0) { fl[i]++; rest--; } });
  const out = {}; values.forEach((v, i) => out[v] = fl[i]); return out;
}

// ---------- section 1 ----------
function renderToets() {
  document.getElementById("subj").textContent = D.subject;
  document.querySelectorAll(".subj2").forEach(x => x.textContent = D.subject);
  const lv = document.getElementById("levels"); lv.innerHTML = "";
  for (const l of D.levels) lv.append(el("button", {class: S.level === l ? "on" : "", onclick: () => { S.level = l; changed(); renderToets(); }}, LEVEL_NL[l]));
  for (const [id, key] of [["title", "title"], ["n_opgaven", "n_opgaven"], ["n_vragen", "n_vragen"], ["duration", "duration"]]) {
    const i = document.getElementById(id); i.value = S[key] === null ? "" : S[key];
    i.oninput = () => { S[key] = i.type === "number" ? (i.value === "" ? null : parseInt(i.value, 10)) : i.value; changed(); if (key === "n_opgaven") renderContexts(); };
  }
  const sel = document.getElementById("tplsel");
  sel.innerHTML = ""; sel.append(el("option", {value: ""}, "—"));
  D.templates.forEach((t, i) => sel.append(el("option", {value: i}, t.name)));
  sel.onchange = () => { if (sel.value !== "") applyTemplate(D.templates[+sel.value].data, D.templates[+sel.value].name); };
  document.getElementById("tplfile").onchange = ev => {
    const f = ev.target.files[0]; if (!f) return;
    const r = new FileReader(); r.onload = () => { try { applyTemplate(JSON.parse(r.result), f.name.replace(/\.json$/, "")); } catch (e) { alert("Geen geldig JSON-bestand."); } };
    r.readAsText(f, "utf-8");
  };
}
function applyTemplate(t, name) {
  if (t.subject && t.subject !== D.subject) { alert("Dit sjabloon is voor " + t.subject + "."); return; }
  if (t.level !== undefined) S.level = t.level;
  for (const k of ["n_opgaven", "n_vragen"]) if (t[k] !== undefined) S[k] = t[k];
  if (t.duration_minutes !== undefined) S.duration = t.duration_minutes;
  if (t.matrix) { S.points = {}; for (const r of t.matrix) S.points[r.group_id] = r.points; }
  if (t.criteria_exclude) { S.exclude = {}; for (const c of t.criteria_exclude) S.exclude[c] = true; }
  if (t.bloom_mix === null) S.bloomMode = "none";
  else if (t.bloom_mix) { S.bloomMode = "set"; S.bloom = roundTo100(t.bloom_mix, D.mix_levels) || {}; }
  if (t.knobs) for (const [k, v] of Object.entries(t.knobs)) {
    const kd = KNOBS.find(x => x.id === k); if (!kd) continue;
    if (v === null) delete S.knobs[k]; else if (v === "vrij") S.knobs[k] = "vrij"; else S.knobs[k] = roundTo100(v, valuesOf(kd));
  }
  if (t.avoid_contexts) S.avoid = t.avoid_contexts.join("\n");
  S.template = name; changed(); renderAll();
}

// ---------- section 2 ----------
function renderMatrix() {
  const box = document.getElementById("matrix"); box.innerHTML = "";
  const byDom = new Map();
  for (const g of D.groups) {
    const dk = g.domein.code; if (!byDom.has(dk)) byDom.set(dk, {d: g.domein, subs: new Map()});
    const sub = byDom.get(dk).subs; const sk = g.subdomein.code; if (!sub.has(sk)) sub.set(sk, {s: g.subdomein, groups: []});
    sub.get(sk).groups.push(g);
  }
  for (const {d, subs} of byDom.values()) {
    box.append(el("h3", {}, d.code + " " + d.title));
    for (const {s, groups} of subs.values()) {
      box.append(el("h4", {}, s.code + " " + s.title));
      const tb = el("table", {}, el("tr", {}, el("th", {}, "punten"), el("th", {}, "leerdoel"), el("th", {}, "id")));
      for (const g of groups) {
        const inp = el("input", {type: "number", min: "0", step: "1", value: S.points[g.group_id] || "", "data-group": g.group_id});
        inp.oninput = () => { const v = parseInt(inp.value, 10); if (v > 0) S.points[g.group_id] = v; else delete S.points[g.group_id]; changed(); };
        const crit = el("ul", {class: "crit"}, g.criteria.map(c => {
          const cb = el("input", {type: "checkbox", checked: S.exclude[c.criterion_id] ? true : null});
          cb.onchange = () => { if (cb.checked) S.exclude[c.criterion_id] = true; else delete S.exclude[c.criterion_id]; changed(); };
          return el("li", {}, el("label", {}, cb, "uitsluiten"), " ", el("b", {}, c.bloom), " ", c.text, " ", el("span", {class: "muted"}, c.criterion_id));
        }));
        tb.append(el("tr", {class: "grouprow"}, el("td", {}, inp),
          el("td", {}, g.goal, el("details", {}, el("summary", {}, g.criteria.length + " criteria"), crit)),
          el("td", {class: "muted"}, g.group_id)));
      }
      box.append(tb);
    }
  }
}

// ---------- section 3 ----------
function renderBloom() {
  const m = document.getElementById("bloommode"); m.innerHTML = "";
  for (const [mode, lab] of [["ask", "Nog niet gekozen (/toets vraagt het)"], ["none", "Geen Bloom-mix (planner kiest)"], ["set", "Bloom-mix instellen"]])
    m.append(el("button", {class: S.bloomMode === mode ? "on" : "", onclick: () => { S.bloomMode = mode; changed(); renderBloom(); }}, lab), " ");
  const box = document.getElementById("bloom"); box.innerHTML = "";
  if (S.bloomMode !== "set") return;
  const ref = refFor("bloom");
  box.append(el("p", {class: "ref"}, ref ? "Centraal examen: Bloom van de gekoppelde punten in de examenbank (" + D.exam_bloom.n_exams + " examen(s))." : "Geen examenreferentie voor Bloom."));
  const rows = el("div", {class: "vals"});
  for (const lv of D.mix_levels) {
    const v = S.bloom[lv] || 0;
    const sl = el("input", {type: "range", min: "0", max: "100", step: "5", value: v});
    const nb = el("input", {type: "number", min: "0", max: "100", step: "1", value: v});
    const live = el("span", {class: "muted"});
    const upd = val => { S.bloom[lv] = Math.max(0, Math.min(100, val || 0)); sl.value = S.bloom[lv]; nb.value = S.bloom[lv];
                         live.textContent = (Math.round(S.bloom[lv] * total()) / 100) + " p"; changed(); bloomSum(); };
    sl.oninput = () => upd(parseInt(sl.value, 10)); nb.oninput = () => upd(parseInt(nb.value, 10));
    live.textContent = (Math.round(v * total()) / 100) + " p";
    rows.append(el("div", {class: "row"}, el("span", {}, lv), sl, nb, el("span", {}, live, "  ", el("span", {class: "ref"}, refText(ref, lv)))));
  }
  box.append(rows, el("p", {id: "bloomsum"}),
    el("p", {}, el("button", {disabled: ref ? null : true, onclick: () => { S.bloom = roundTo100(ref.pooled, D.mix_levels) || {}; changed(); renderBloom(); }}, "Zet op eindexamen"), " ",
                el("button", {onclick: () => { S.bloom = {}; changed(); renderBloom(); }}, "Reset")));
  bloomSum();
}
function bloomSum() {
  const p = document.getElementById("bloomsum"); if (!p) return;
  const s = D.mix_levels.reduce((a, l) => a + (S.bloom[l] || 0), 0);
  p.className = s === 100 ? "ok" : "warn"; p.textContent = "Som: " + s + " %" + (s === 100 ? "" : " (moet 100 % zijn)");
}

// ---------- section 4 ----------
function renderKnobs() {
  document.getElementById("reflabel").textContent = D.reference.label + (D.reference.provisional && D.reference.source !== "none" ? " — voorlopig" : "");
  const box = document.getElementById("knobs"); box.innerHTML = "";
  for (const k of KNOBS) box.append(knobBlock(k));
  for (const k of COMPUTED) {
    const ref = refFor(k.id);
    box.append(el("div", {class: "knob"}, el("div", {class: "head"}, el("b", {}, k.label), el("span", {class: "state"}, "berekend, niet in te stellen"),
      el("span", {class: "ref"}, typeof k.definition === "string" ? k.definition : "")),
      el("div", {class: "vals"}, valuesOf(k).map(v => el("div", {class: "row"}, el("span", {}, v), el("span", {}), el("span", {}), el("span", {class: "ref"}, refText(ref, v)))))));
  }
}
function knobBlock(k) {
  const wrap = el("div", {class: "knob", "data-knob": k.id});
  const ref = refFor(k.id), st = S.knobs[k.id], values = valuesOf(k);
  const stateTxt = st === undefined ? "niet ingesteld" : st === "vrij" ? "vrij (planner kiest)" : "aandelen";
  const setRef = () => { S.knobs[k.id] = roundTo100(ref.pooled, values) || Object.fromEntries(values.map(v => [v, 0])); changed(); rerender(); };
  const rerender = () => wrap.replaceWith(knobBlock(k));
  wrap.append(el("div", {class: "head"}, el("b", {}, k.label), el("span", {class: "state"}, stateTxt),
    el("button", {disabled: ref ? null : true, onclick: setRef}, "Zet op eindexamen"),
    el("button", {class: st === "vrij" ? "on" : "", onclick: () => { S.knobs[k.id] = "vrij"; changed(); rerender(); }}, "Vrij"),
    el("button", {onclick: () => { S.knobs[k.id] = Object.fromEntries(values.map(v => [v, 0])); changed(); rerender(); }}, "Zelf instellen"),
    el("button", {onclick: () => { delete S.knobs[k.id]; changed(); rerender(); }}, "Reset"),
    APPLIES_NOTE[k.id] ? el("span", {class: "note"}, APPLIES_NOTE[k.id]) : null));
  if (typeof k.definition === "string") wrap.append(el("div", {class: "ref"}, k.definition));
  const rows = el("div", {class: "vals"});
  for (const v of values) {
    const def = typeof k.definition === "object" ? (k.definition[v] || "") : "";
    if (st && st !== "vrij") {
      const cur = st[v] || 0;
      const sl = el("input", {type: "range", min: "0", max: "100", step: "5", value: cur});
      const nb = el("input", {type: "number", min: "0", max: "100", step: "1", value: cur});
      const upd = val => { st[v] = Math.max(0, Math.min(100, val || 0)); sl.value = st[v]; nb.value = st[v]; changed(); sumLine(); };
      sl.oninput = () => upd(parseInt(sl.value, 10)); nb.oninput = () => upd(parseInt(nb.value, 10));
      rows.append(el("div", {class: "row", title: def}, el("span", {}, valueLabel(k, v)), sl, nb, el("span", {class: "ref"}, refText(ref, v))));
    } else {
      rows.append(el("div", {class: "row", title: def}, el("span", {}, valueLabel(k, v)), el("span", {}), el("span", {}), el("span", {class: "ref"}, refText(ref, v))));
    }
  }
  const sumP = el("div", {class: "vals"});
  const sumLine = () => { if (!st || st === "vrij") return; const s = values.reduce((a, v) => a + (st[v] || 0), 0);
    sumP.className = "vals " + (s === 100 ? "ok" : "warn"); sumP.textContent = "Som: " + s + " %" + (s === 100 ? "" : " (moet 100 % zijn)"); };
  sumLine();
  wrap.append(rows, sumP);
  return wrap;
}

// ---------- section 5, 6 ----------
function renderContexts() {
  const box = document.getElementById("ctxfixed"); box.innerHTML = "";
  const n = S.n_opgaven || 0;
  box.append(el("p", {class: "note"}, "Optioneel: een vaste context per opgave. Leeg = de straat stelt een context voor."));
  for (let i = 1; i <= n; i++) {
    const inp = el("input", {type: "text", value: S.contexts[i] || "", placeholder: "bijv. kapsalon met twee vestigingen"});
    inp.oninput = () => { if (inp.value.trim()) S.contexts[i] = inp.value; else delete S.contexts[i]; changed(); };
    box.append(el("p", {}, el("label", {}, "Opgave " + i, inp)));
  }
  const av = document.getElementById("avoid"); av.value = S.avoid; av.oninput = () => { S.avoid = av.value; changed(); };
  const h = document.getElementById("history"); h.innerHTML = "";
  if (!D.contexts.length) h.append(el("p", {class: "muted"}, "Nog geen eerdere toetsen in de toetsbank."));
  else h.append(el("ul", {}, D.contexts.map(c => el("li", {}, c.date + " · " + c.title + " (" + c.context_tags.join(", ") + ") · " + c.toets_id))));
}
function renderReuse() {
  const box = document.getElementById("reuse"); box.innerHTML = "";
  if (!D.reuse.length) { box.append(el("p", {class: "muted"}, "Geen opgaven in de toetsbank voor deze criteriaversie.")); return; }
  const tb = el("table", {}, el("tr", {}, el("th", {}, ""), el("th", {}, "opgave"), el("th", {}, "toets"), el("th", {}, "punten"), el("th", {}, "leerdoelen")));
  for (const r of D.reuse) {
    const key = r.toets_id + "/" + r.opgave_id;
    const cb = el("input", {type: "checkbox", checked: S.reuse[key] ? true : null});
    cb.onchange = () => { if (cb.checked) S.reuse[key] = true; else delete S.reuse[key]; changed(); };
    tb.append(el("tr", {}, el("td", {}, cb), el("td", {}, r.title), el("td", {}, r.toets_title + " (" + r.toets_id + ")"), el("td", {}, r.points),
      el("td", {}, Object.entries(r.groups).map(([g, p]) => g + ": " + p).join(", "))));
  }
  box.append(tb, el("p", {class: "note"}, "Hergebruikte opgaven blijven letterlijk en tellen mee in de matrijs en de aandelen."));
}

// ---------- order + validation ----------
function shareMap(st, values) {
  const s = values.reduce((a, v) => a + (st[v] || 0), 0); if (!s) return null;
  const out = {}; let acc = 0, last = null;
  for (const v of values) if (st[v] > 0) { out[v] = Math.round(st[v] / s * 1000) / 1000; acc += out[v]; last = v; }
  if (last) out[last] = Math.round((out[last] + 1 - acc) * 1000) / 1000;
  return out;
}
function buildOrder(asTemplate) {
  const o = {subject: D.subject, level: S.level};
  if (asTemplate) o.name = document.getElementById("tplname").value.trim() || "sjabloon"; else o.title = S.title.trim() || null;
  o.criteria_run = D.criteria_run; o.n_opgaven = S.n_opgaven; o.n_vragen = S.n_vragen; o.duration_minutes = S.duration || null;
  o.matrix = D.groups.filter(g => S.points[g.group_id] > 0).map(g => ({group_id: g.group_id, points: S.points[g.group_id]}));
  o.criteria_include = null;
  const ex = Object.keys(S.exclude).filter(c => S.exclude[c]); o.criteria_exclude = ex.length ? ex.sort() : null;
  if (S.bloomMode === "none") o.bloom_mix = null;
  else if (S.bloomMode === "set") o.bloom_mix = shareMap(S.bloom, D.mix_levels);
  o.knobs = {};
  for (const k of KNOBS) { const st = S.knobs[k.id]; if (st === undefined) continue; o.knobs[k.id] = st === "vrij" ? "vrij" : shareMap(st, valuesOf(k)); }
  const av = S.avoid.split(/[\n,]/).map(x => x.trim()).filter(Boolean); o.avoid_contexts = av.length ? av : null;
  if (!asTemplate) {
    const ctx = Object.entries(S.contexts).filter(([i, c]) => c && +i <= (S.n_opgaven || 0)).map(([i, c]) => ({opgave: +i, context: c}));
    o.contexts = ctx.length ? ctx : null;
    o.reuse = Object.keys(S.reuse).filter(k => S.reuse[k]).map(k => { const [t, og] = k.split("/"); return {toets_id: t, opgave_id: og}; });
    o.reference = D.reference.code;
    if (S.template) o.template = S.template;
  }
  return o;
}
function problems() {
  const p = [], w = [];
  if (total() <= 0) p.push("De matrijs heeft nog geen punten.");
  if (S.n_opgaven && S.n_vragen && S.n_vragen < S.n_opgaven) p.push("Het aantal vragen is kleiner dan het aantal opgaven.");
  if (S.n_vragen && total() && S.n_vragen > total()) p.push("Er zijn meer vragen dan punten.");
  if (S.bloomMode === "set") { const s = D.mix_levels.reduce((a, l) => a + (S.bloom[l] || 0), 0); if (s !== 100) p.push("De Bloom-mix telt op tot " + s + " %, niet 100 %."); }
  for (const k of KNOBS) {
    const st = S.knobs[k.id];
    if (st === undefined) w.push(k.label + ": niet ingesteld — /toets vraagt het.");
    else if (st !== "vrij") { const s = valuesOf(k).reduce((a, v) => a + (st[v] || 0), 0); if (s !== 100) p.push(k.label + ": aandelen tellen op tot " + s + " %, niet 100 %."); }
  }
  for (const [f, lab] of [["title", "titel"], ["level", "niveau"], ["n_opgaven", "aantal opgaven"], ["n_vragen", "aantal vragen"]])
    if (!S[f]) w.push("Geen " + lab + " — /toets vraagt het.");
  if (S.bloomMode === "ask") w.push("Bloom-mix: nog niet gekozen — /toets vraagt het.");
  return {p, w};
}
function changed() {
  save();
  document.getElementById("topsum").textContent = "Totaal " + total() + " punten · " + Object.keys(S.points).length + " leerdoelen · "
    + (S.n_opgaven || "?") + " opgaven · " + (S.n_vragen || "?") + " vragen · " + D.reference.label;
  document.getElementById("mtotal").textContent = "(totaal " + total() + " punten)";
  const {p, w} = problems(), ul = document.getElementById("messages"); ul.innerHTML = "";
  for (const x of p) ul.append(el("li", {class: "warn"}, x));
  for (const x of w) ul.append(el("li", {class: "muted"}, x));
  if (!p.length) ul.append(el("li", {class: "ok"}, "Klaar om te downloaden."));
  document.getElementById("dl").disabled = p.length > 0;
}
function download(name, obj) {
  const blob = new Blob([JSON.stringify(obj, null, 2) + "\n"], {type: "application/json"});
  const a = el("a", {href: URL.createObjectURL(blob), download: name}); document.body.append(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}
function renderAll() { renderToets(); renderMatrix(); renderBloom(); renderKnobs(); renderContexts(); renderReuse(); changed(); }

document.getElementById("dl").onclick = () => download("toetsopdracht.json", buildOrder(false));
document.getElementById("dltpl").onclick = () => { const o = buildOrder(true); download((o.name || "sjabloon") + ".json", o); };
document.getElementById("clear").onclick = () => { try { localStorage.removeItem(STORE); } catch (e) { } location.reload(); };

if (location.hash !== "#selftest") load();
renderAll();
if (location.hash === "#selftest") {   // used by tests/run_toets_fixture.py with a headless browser
  S.title = "Zelftest"; S.level = "5vwo"; S.n_opgaven = 2; S.n_vragen = 4;
  D.groups.slice(0, 2).forEach((g, i) => S.points[g.group_id] = 6 - 2 * i);
  for (const k of KNOBS) { const r = refFor(k.id); S.knobs[k.id] = r ? roundTo100(r.pooled, valuesOf(k)) : "vrij"; }
  S.bloomMode = "none"; renderAll();
  const t = document.getElementById("selftest");
  t.textContent = JSON.stringify({order: buildOrder(false), problems: problems().p, rows: document.querySelectorAll("tr.grouprow").length,
                                  knobs: document.querySelectorAll("#knobs .knob").length});
}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main(sys.argv)
