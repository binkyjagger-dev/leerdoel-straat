# 30 — Toets-straat: overview

**Status:** draft v0.1 (2026-11-13) · **Owner:** Martijn (teacher, decides) · **Architect/PO:** Claude ·
**Decisions:** §5 and [docs/plan-toets-straat.md](../docs/plan-toets-straat.md) §2.

## 1. Purpose

A fourth pipeline in this repo, `/toets`, that generates a **toets** (a school test in the style of
the CvTE central exam) for one subject: opgaven (a context block with sources) holding vragen, each
vraag split into scorepunten, with a correctievoorschrift. The teacher steers it with:

- a **toetsmatrijs**: points per leerdoel (group of the subject's criteria run), plus an optional
  Bloom mix for the whole toets;
- the **number of opgaven and vragen**;
- **level knobs** (§3): per knob the teacher sets the share for this toets, shown next to the
  share in the subject's central exams (the **reference profile**).

The generator works from a **pattern catalogue** in two layers — a base layer shared by all subjects
and a subject layer — and sees real exam questions of the same pattern as style examples.

Output per run: student version, correctievoorschrift and a verantwoording (planned vs realised vs
central exam) as Word + Markdown, figures as PNG, a doubt list. Every toets is added to the
subject's **toetsbank**, which also keeps the context history so contexts do not repeat.

## 2. What is shared with the other straten

| Reused | From | How |
|---|---|---|
| Criteria (leerdoel + succescriteria + Bloom, ids) | `/generate`, via the exam bank's `criteria.json` | the toets is bound to the bank's criteria version |
| Subject profile, decisions, glossary | specs/06 | read by every agent via `decisions_snapshot.json` |
| Scorepunt links and Bloom per scorepunt of real exams | `/examen` bank (specs/25) | style examples, reference profile |
| Pattern and knob labels per exam question | new `/examen` step E7 (specs/26) | catalogue statistics, reference profile |
| Two-judge + fresh-verifier discipline, bounded repair, doubt list | specs/04, 14, 24 | §4 |

New in this straat: the order (specs/32), the blueprint with a teacher review (specs/33), a **blind
solver** and deterministic recomputation of every calculation (specs/34), figure rendering, Word
export and the toetsbank (specs/35).

## 3. Level knobs (summary; full model in specs/31)

| Knob | Values (ordinal where it matters) | Applies to |
|---|---|---|
| `pattern` | catalogue codes (P01…, B01…, E-codes per subject) | every vraag |
| `solo` | unistructureel < multistructureel < relationeel < uitgebreid abstract | every vraag |
| `route` | gegeven < zelf vinden | calculation patterns |
| `steps` | 1, 2, 3, 4+ | every vraag |
| `sources` | in vraagtekst < één bron zonder ruis < meerdere bronnen met ruis | every vraag |
| `claim` | nee < ja (the stem holds a claim/stelling to judge) | every vraag |
| `new_concept` | nee < ja (a concept outside the criteria is introduced in the stem) | every vraag |
| `schema` | geen, voorgestructureerd < deels ingevuld | schema patterns (B02, tables in P10) |
| `builds_on` | nee < ja (uses the outcome of an earlier vraag of the same opgave) | every vraag except the first of an opgave |
| `combination` | 1, 2, 3 leerdoelen | **computed** from the scorepunt links, not set |
| `bloom` | revised Bloom | **set via the matrix's Bloom mix**, per scorepunt |

Shares are by points (specs/32 §1). The reference profile shows the central-exam share per value;
the teacher's order states the share for this toets.

## 4. Pipeline in one picture

```
subjects/<s>/examenbank/  (criteria.json, links/, labels/, profiel/referentieprofiel.json)
subjects/<s>/toets/       (patterns.json, contexten.md, sjablonen/)      data/toets/ (patterns_base.json, knobs.json)
   │
[T0  form_build.py] ──► toetsformulier-<s>.html  ──(teacher fills, downloads)──► toetsopdracht.json
   │
[T1  order: /toets asks the missing knobs with buttons] ──► 31_order.json ──► PAUSE 1 (confirm order)
   │
[T2  toets-planner] ──► 32_blueprint.json ◄── blueprint_check.py (matrix exact, Bloom mix, knob shares, history)
   │        blueprint_report.py ──► output/bouwplan.md ──► PAUSE 2 (approve / change) ──► 32_blueprint_review.json
   │        blueprint_apply.py + blueprint_check.py
   │
[T3  toets-writer ×1 per opgave] ──► 33_items/<opgave>.json   (+ exam_examples.py: style examples, overlap_check.py)
   │        calc_check.py (recompute every calculation) · figures.py (render) · items_check.py
   │
[T4  toets-solver (blind, fresh) per opgave] ──► 34_solutions/<opgave>.json ──► solver_compare.py
[T4  item-labeller A/B (blind, toets mode)]  ──► 34_labels.{A,B}/<opgave>.json ──► label_merge.py ──► realized.py
   │
[T5  toets-verifier (fresh)] ──► 35_verification.json ──► toets-writer R (max 2 rounds) ──► T3 checks again
   │
[T6  export_toets.py] ──► output/*.docx, *.md, figuren/*.png, verantwoording, twijfellijst
[T6  toetsbank_add.py] ──► subjects/<s>/toetsbank/
```

## 5. Decisions taken 2026-11-13 (Martijn)

1. A fourth straat in this repo: command `/toets`, specs 30–35, plus specs/26 for the `/examen`
   extension.
2. Level: no fixed presets. For every knob the straat shows the **central-exam reference** (share
   per value); the teacher sets the share for this toets per knob. The planner distributes the
   shares over the vragen; in the blueprint the teacher can override per vraag.
3. Toetsmatrijs: points per leerdoel **plus** an optional Bloom mix for the whole toets.
4. Input: **both** a local HTML form (matrix and knobs) and buttons in `/toets` for whatever the
   order file leaves open.
5. Reference profile: a new `/examen` step labels every exam question with pattern + knob values
   (two labellers); the profile is **stored per subject** and is **rebuilt whenever exams are added**
   to the bank (specs/26). Seeded from the analyses of November 2026.
6. **Two pauses**: the order (1) and the blueprint (2). Nothing is written before the teacher
   approves the blueprint.
7. No separate "begrijpen per leerdoel" rule: the Bloom mix of the matrix governs it; the blueprint
   shows per leerdoel which criteria are and are not tested.
8. Output: Word + Markdown — student version, correctievoorschrift, verantwoording. The
   verantwoording shows the knobs **planned (order) vs realised (labelled) vs central exam
   (reference)**, and the matrix and Bloom mix planned vs realised.
9. Contexts: the straat proposes them; contexts in the subject's history are avoided; the teacher can
   replace them in the blueprint.
10. Verification: a **blind solver** (fresh agent, no correctievoorschrift), scripts that recompute
    every calculation and check points against the matrix, a **fresh verifier** for criterion,
    pattern, knobs and unambiguity. Max 2 repair rounds; leftovers to the doubt list.
11. Form: a **local HTML file** generated per subject (`/toets --formulier <vak>`), no server.
12. Figures: the straat draws them (writer delivers figure data, `figures.py` renders with
    matplotlib); tables and schemas become Word tables.
13. Style examples: the writer sees 1–2 real exam questions per pattern from the bank's exams, with
    an **overlap check** against copying.
14. Toetsbank per subject (`subjects/<vak>/toetsbank/`, committed): every toets with its labels;
    opgaven can be reused in a new toets; the context history lives there.
15. Scope v1: **bedrijfseconomie and economie, VWO 4–6**; reference = VWO central exam. HAVO later.

16. Knob shares and the Bloom mix are **by points**.
17. A new base pattern **P16 Kennisvraag (noem of omschrijf)** covers *onthouden*; it is marked
    "niet in centraal examen" (reference 0 %).
18. Tolerances: Bloom mix ±5 percentage points per level, knob shares ±10 pp, always at least one
    vraag of slack (specs/32 §4). Points per leerdoel are exact.
19. `builds_on` only inside one opgave.

Architect defaults (listed in the plan §3, confirm or change): reused opgaven are verbatim and count
in the matrix; python-docx for Word; the order's `level` sets no knob values (it goes to the writer
for language and context); orders can be saved as templates per subject.

## 6. Documents

| File | Contents |
|---|---|
| [26-examen-labels.md](26-examen-labels.md) | `/examen` step E7: pattern + knob labels per exam question, reference profile, catalogue statistics, updating with new exams |
| [31-toets-catalogue-knobs.md](31-toets-catalogue-knobs.md) | Pattern catalogue (base + subject), knob definitions, pattern–knob–Bloom compatibility, how patterns are added |
| [32-toets-order.md](32-toets-order.md) | The order (`toetsopdracht.json`), the HTML form, the button dialogue, tolerances |
| [33-toets-pipeline.md](33-toets-pipeline.md) | Command, roles, run files, both pauses, orchestration, repair, cost |
| [34-toets-verification.md](34-toets-verification.md) | Deterministic checks (incl. calculation recomputation, overlap), blind solver, labeller, verifier rubric |
| [35-toets-export-bank.md](35-toets-export-bank.md) | Word/Markdown outputs, verantwoording, figures, toetsbank, context history, reuse |

## 7. Definition of done (v1)

1. `/toets` produces a bedrijfseconomie 5 VWO toets (3–4 opgaven, 10–12 vragen, ~30 points, on F2
   leerdoelen) with only the two pauses as human input.
2. Points per leerdoel equal the matrix exactly; the realised Bloom mix and knob shares are within
   tolerance (specs/32 §4), or the deviation is in the verantwoording with a reason.
3. Every calculation in the correctievoorschrift is recomputed by `calc_check.py` from the data in the
   stem/sources and matches; every number in a figure equals the number in the data.
4. The blind solver's answers match the correctievoorschrift on every calculation vraag, or the vraag
   is repaired or on the doubt list.
5. No 8-word sequence of a style example appears in the toets (`overlap_check.py`).
6. The same for economie 5 VWO once its exam bank and labels exist (specs/26 §6).
7. Martijn's review: ≥ 8 of 10 vragen usable without rewriting (acceptance, not automated).
