# 10 — Methode-straat: overview

**Status:** draft v0.1 (2026-10-22) · **Owner:** Martijn · **Decided:** see §5.

## 1. Purpose

A second pipeline in this repo, `/koppel`, that links the success criteria
produced by `/generate` to a textbook (*methode*): first to its chapters and
paragraphs (part A), then to the sub-questions of its exercises (part B).
Students see, per learning goal group, where they learn it and where they
practise it. Teachers see gaps in the method and method content outside the
syllabus.

Input: a `/generate` run (its `04_groups_student.json`, criterion ids are the
key) and the method's PDF(s). Output: mapping CSVs, two gap reports, a sample
list for the teacher, and a confidence score per link.

## 2. What is different from the leerdoel-straat

`/generate` creates something new from one source. `/koppel` relates two
existing things, and a link can be wrong in two directions: missing
(*recall*) or unjustified (*precision*). Three principles follow:

- **Evidence.** No link without a verbatim quote (≤ 25 words) from the
  paragraph or question. The quote is checked deterministically.
- **Order decides "leert".** The judges only say *whether* a paragraph
  explains, practises or merely mentions a criterion. A script then assigns
  the gradation from book order (first explanation = *leert*). Reproducible,
  no second judgement.
- **Two-way verification.** Precision on a sample of links; recall per
  paragraph ("which criteria belong here that are not linked?").

## 3. Pipeline in one picture

```
method.pdf                              runs/<generate-run>/04_groups_student.json
   │                                                  │
   ▼                                                  │
[M1 method-ingest] ──► 11_method_units.json (+ text in run dir only)
   │
   ▼
[M1b intake] ──► PAUSE → subjects/<s>/decisions.json (+ methodes/<m>/profile.md read)
   │
   ▼
[M2 candidates] (script) ──► 12_candidates.json       criterion → 3–6 paragraphs
   │
   ▼
[M3 judge ×2] (agents, fresh) ──► 13_judgements.{A,B}.json   explains / practises / mentions / none + quote
   │
   ▼
[M4 gradation] (script) ──► 14_mappings.json          leert / herhaalt / oefent / noemt + confidence
   │
   ▼
[M5 mapping-verifier] (agent, fresh) ──► 15_verification.json   precision sample + recall per paragraph
   │        └── disputed/low → repair judge (1 round) or sample list
   ▼
[M6 export] ──► output/koppelingen_paragraaf.csv, gaten_methode.md, buiten_syllabus.md, steekproef.md
```

Part B (exercises) adds M7–M9 after M6; see [13-methode-pipeline.md](13-methode-pipeline.md) §4.

## 4. Documents

| File | Contents |
|---|---|
| [11-methode-units.md](11-methode-units.md) | Method unit model (chapter → paragraph → exercise → sub-question), ingest adapters, what is stored |
| [12-mapping-model.md](12-mapping-model.md) | Link model, gradations, confidence, quote rules, ownership |
| [13-methode-pipeline.md](13-methode-pipeline.md) | Roles, files, orchestration, repair, part B |
| [14-mapping-verification.md](14-mapping-verification.md) | Deterministic checks, judge rubric, verifier (precision/recall), baseline comparison |
| [15-mapping-export.md](15-mapping-export.md) | CSV schemas (Doelstellr-ready), reports, run layout |

## 5. Decisions taken 2026-10-22

1. Four gradations (*leert*, *oefent*, *herhaalt*, *noemt*); *leert* = first
   paragraph in book order that explains the criterion; exactly one per
   criterion. A criterion explained in two parts: first = leert, second =
   herhaalt with note "breidt uit".
2. Two independent judges per link; agreement drives confidence.
3. Baseline by hand first (LWEO lesbrief *Vraag en aanbod*, H1–H2); the straat
   is built in parallel and measured against it.
4. Key = criterion ids from `/generate` (`D1.16-01-c`); Doelstellr ids in a
   translation table.
5. Same repo, one `/koppel` command, specs 10–15.
6. Stored quotes ≤ 25 words; method text stays in the run folder, never in output.
7. Book order (volumes, years) is declared in the method profile.

## 6. Definition of done (part A, v1)

1. `/koppel` runs on H1–H2 of the baseline lesbrief without human input
   except the intake.
2. Against the hand baseline: precision ≥ 90 %, recall ≥ 85 % on *leert* and
   *oefent* links.
3. Every criterion in scope has exactly one *leert* or is listed in the method
   gap report; every paragraph has ≥ 1 link or is listed as outside-syllabus.
4. Every stored quote is verbatim in its paragraph (OCR-tolerant match).
5. Martijn's stratified sample (10 high / 10 low confidence): high ≥ 95 %
   correct; low clearly worse — the confidence score discriminates.
