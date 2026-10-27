"""Shared helpers for the examen-straat scripts. Reuses the methode-straat helpers (quotes, Bloom rules)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parent / "mapping"))
from common import BLOOM_ORDER, ROOT, bloom_rank, load_bloom_rules  # noqa: E402,F401
from mcommon import (MAX_QUOTE_WORDS, Report, load_json, norm, quote_in_text, read_text,  # noqa: E402,F401
                     save_json, stems, validate_schema, words)
from ex_merge import computed, verb_levels  # noqa: E402,F401
from check_ex_mappings import verb_in_text as _verb_in_text  # noqa: E402

CONF = ["low", "medium", "high"]


def verb_in_text(verb: str, text: str) -> bool:
    """As the methode-straat check, plus the imperative with a doubled vowel: 'motiveren' ~ 'motiveer',
    'analyseren' ~ 'analyseer', 'beredeneren' ~ 'beredeneer'."""
    if _verb_in_text(verb, text):
        return True
    v = norm(verb).split()[0] if norm(verb) else ""
    root = v[:-2] if v.endswith("en") else v
    m = re.match(r"^(.*[^aeiou])([aeiou])([^aeiou])$", root)
    return bool(m) and (m.group(1) + m.group(2) * 2 + m.group(3)) in norm(text)


def validate_def(data, schema_name: str, definition: str) -> list[str]:
    """Validate against #/$defs/<definition> of a schema file."""
    import jsonschema
    schema = load_json(ROOT / "schemas" / schema_name)
    sub = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{definition}"}
    v = jsonschema.Draft202012Validator(sub)
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(v.iter_errors(data), key=lambda e: list(e.absolute_path))]


class Units:
    """21_exam_units.json, indexed."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.data = load_json(run_dir / "21_exam_units.json")
        self.exams = {e["exam_id"]: e for e in self.data["exams"]}
        self.by_id = {u["unit_id"]: u for u in self.data["units"]}
        self.opgaven = [u for u in self.data["units"] if u["kind"] == "opgave"]
        self.questions = [u for u in self.data["units"] if u["kind"] == "question"]
        self.scorepunten = [u for u in self.data["units"] if u["kind"] == "scorepunt"]

    def tolerant(self, exam_id: str) -> bool:
        return self.exams[exam_id]["text_extraction"] in ("ocr", "mixed")

    def question_text(self, qid: str) -> str:
        return read_text(self.run_dir, self.by_id[qid].get("text_ref"))


def ask_of(question_text: str) -> str:
    """The question's own ask: the text after the '[vraag]' marker."""
    i = question_text.find("[vraag]")
    return question_text[i + len("[vraag]"):].strip() if i >= 0 else question_text


def criteria_index(groups_doc: dict) -> dict[str, dict]:
    out = {}
    for g in groups_doc["groups"]:
        for c in g["criteria"]:
            out[c["criterion_id"]] = {"group_id": g["group_id"], "unit_id": g["unit_id"], "bloom": c["bloom"],
                                      "text_expert": c["text_expert"], "text_student": c.get("text_student", ""),
                                      "goal_expert": g["goal"]["text_expert"],
                                      "goal_student": g["goal"].get("text_student", ""),
                                      "concepts": g.get("concepts", [])}
    return out


def quote_valid(quote: str | None, text: str, tolerant: bool) -> bool:
    if not quote or words(quote) > MAX_QUOTE_WORDS:
        return False
    return quote_in_text(quote, text, tolerant)[0]
