# 02 — Learning goal groups

## 1. Definition

A **learning goal group** is the unit of output.

```json
{
  "group_id": "D1.1-01",                 // <unit_id>-<nn>
  "unit_id": "D1.1",                     // exactly one leaf source unit
  "source_quote": "… verklaren hoe prijsvorming tot stand komt …",
  "goal": {
    "text_expert": "De leerling kan verklaren hoe de evenwichtsprijs ontstaat uit vraag en aanbod.",
    "text_student": "Ik kan uitleggen hoe de evenwichtsprijs ontstaat door vraag en aanbod.",
    "bloom": "begrijpen"                 // computed: max(criteria.bloom)
  },
  "criteria": [
    {
      "criterion_id": "D1.1-01-a",
      "text_expert": "Benoemt dat de evenwichtsprijs de prijs is waarbij gevraagde en aangeboden hoeveelheid gelijk zijn.",
      "text_student": "Ik kan benoemen dat bij de evenwichtsprijs de gevraagde en aangeboden hoeveelheid gelijk zijn.",
      "bloom": "onthouden",
      "bloom_verb": "benoemen"
    },
    {
      "criterion_id": "D1.1-01-b",
      "text_expert": "Legt uit waarom een prijs boven evenwicht tot een aanbodoverschot leidt en daalt.",
      "text_student": "Ik kan uitleggen waarom een prijs boven het evenwicht zorgt voor een aanbodoverschot en daardoor daalt.",
      "bloom": "begrijpen",
      "bloom_verb": "uitleggen"
    }
  ],
  "provenance": {
    "generated_round": 1,
    "generator_notes": "Eindterm bevat ook 'berekenen'; apart in groep D1.1-02."
  }
}
```

Cardinality
- One group → exactly one leaf `unit_id`. (Textbook + syllabus dual links come later via `related_unit_ids` on the unit, not on the group.)
- One leaf → ≥ 1 group. The planner decides how many (see 03-pipeline §2).
- One group → 2–4 criteria. One criterion = one observable performance.

## 2. Bloom rules (revised taxonomy, cognitive process dimension)

Six levels, Dutch labels used throughout:

| Level (nl) | Level (en) | Typical verbs (subset; full list in `data/bloom_verbs_nl.json`) |
|---|---|---|
| onthouden | remember | benoemen, noemen, omschrijven, herkennen, opsommen, definiëren |
| begrijpen | understand | uitleggen, verklaren, samenvatten, toelichten, een voorbeeld geven, classificeren, vergelijken, interpreteren |
| toepassen | apply | berekenen, toepassen, uitvoeren, gebruiken, aflezen, tekenen (van een gegeven model), oplossen |
| analyseren | analyze | analyseren, onderscheiden, verband leggen, afleiden, verklaren aan de hand van (bron), onderbouwen met gegevens |
| evalueren | evaluate | beoordelen, beargumenteren, afwegen, kritisch bespreken, een standpunt innemen en verdedigen |
| creëren | create | ontwerpen, opstellen (van een plan/model), formuleren (van een eigen hypothese), construeren |

Rules
1. **Bloom is a property of the criterion.** Every criterion has `bloom` and
   `bloom_verb`. `bloom_verb` must be the infinitive of the main verb in
   `text_expert` and must appear in the verb list of that level.
2. **Goal Bloom is computed**, not generated: `goal.bloom = max(criteria.bloom)`
   on the ordinal onthouden < begrijpen < toepassen < analyseren < evalueren < creëren.
   `scripts/bloom_check.py` computes and overwrites it.
3. **Source-implied level.** The planner reads the eindterm's own verbs
   ("beschrijven", "verklaren", "berekenen", "beoordelen") and sets a
   `target_bloom_max` per unit. The group's goal Bloom may not exceed
   `target_bloom_max` by more than one level (constructive alignment: don't
   ask students for evaluation on an eindterm that asks for description).
   Lower criteria are always allowed as scaffolding.
4. **Forbidden criterion verbs** (not observable; Mager): weten, kennen,
   begrijpen, inzien, beseffen, bekend zijn met, leren, zich bewust zijn van.
   Allowed in a goal only when immediately made observable by the criteria;
   never as a criterion verb.
5. Ambiguous verbs ("verklaren" can be begrijpen or analyseren; "tekenen" can be
   toepassen or creëren) are resolved by context in the generator and checked by
   the verifier; the verb list marks these as `ambiguous: true` with the
   allowed levels.

## 3. Quality rules for the expert formulation

- Goal names **one** central concept or skill. If the eindterm bundles several,
  split into several groups (planner's job).
- Criteria are **observable performances** a teacher could tick off from
  student work or speech: product (what is produced), process (what is done),
  or condition (under what constraint). No attitudes, no "begrijpt".
- Criteria together make the goal **checkable**: if a student meets all
  criteria, the goal is met. If one criterion already covers the whole goal,
  the group is too thin or the goal too narrow.
- Criteria are **distinct**: no two criteria of the same group restate each
  other at different Bloom levels unless the higher one adds a performance.
- Economics terminology is kept (evenwichtsprijs, elasticiteit, marginale
  kosten): the term *is* the learning content. Explanations of terms belong in
  the lesson, not in the goal.

## 4. Student-language rules

The literature does not prescribe a readability level like B1. What it does
say, consistently (Clarke; Hattie; Wiliam; Marzano; SLO guidance on
*leerdoelen in leerlingentaal*), is that goals and criteria work when students
can read them without the teacher, use them to self-assess, and recognise when
they have met them. The rules below operationalise that.

1. **Form.** Every goal and every criterion starts with **"Ik kan"** followed by
   an action verb. No "Ik weet", "Ik begrijp", "Ik ken" — those are not
   checkable by the student either.
2. **One sentence, one idea.** Maximum ~20 words per sentence. One main clause,
   at most one subordinate clause. No semicolons, no enumerations inside a
   sentence (split into criteria instead).
3. **Concrete and observable from the student's side.** The student must be
   able to answer "kan ik dit al?" with yes or no. Prefer "berekenen",
   "uitleggen aan een klasgenoot", "aflezen uit een grafiek" over "inzicht
   hebben in".
4. **Active voice, present tense, second person implied.** No passive
   constructions ("er wordt verklaard"), no nominalisations ("het verklaren van").
5. **Subject terms stay; procedural jargon goes.** Keep economic terms
   (they are the content). Remove curriculum jargon: "de kandidaat", "in de
   context van", "met inachtneming van", "aan de hand van onderstaande".
   Replace "de kandidaat kan" with "Ik kan".
6. **Context cue when it helps.** Where the eindterm names a context
   ("in een situatie van marktfalen"), keep a short, concrete cue a student
   recognises ("bij een markt die niet goed werkt, zoals bij vervuiling").
7. **Meaning preserved.** The student text must not add, drop or soften a
   performance relative to `text_expert`. In particular the Bloom verb
   category must survive: "verklaren" may become "uitleggen waarom", not
   "noemen".
8. **No vague quantifiers or hedges.** "Enkele", "een aantal", "in grote
   lijnen", "globaal", "ongeveer" are removed unless the eindterm requires
   approximation (then make it concrete: "schatten").
9. **Readability check (deterministic, advisory):** mean sentence length,
   words > 3 syllables ratio, presence of forbidden phrases. Hard fail only on
   forbidden openers and forbidden verbs; the rest is reported.

Reference for later tuning: when Martijn has classroom feedback, the rules
above are the knobs; they live in `data/student_language_rules.json` so the
agent prompt and the validator read the same list.
