"""Deterministic text measures shared by scripts/exam/exam_metrics.py (the CE house rules) and items_check.py (the toets
checks), so the central exam and the toets are measured with the same instrument (specs/36 §3.1, §5.1–§5.2, §11 B4,
B9).

- words(text): whitespace tokens (table cells included when the caller passes their text) — §11 B9
- sentences(text): the text split after . ? ! (before a capital, a digit, a quote or the end)
- count_tasks(task, rules): §5.2 — per sentence: a helper sentence (asking_verbs.json `helpers`: "Licht je antwoord
  toe", "Motiveer", any sentence with "hiervoor", "Gebruik …", "Betrek …", "Ga uit van", "Rond … af") counts 0; a
  sentence that starts with an asking verb or ends in "?" counts 1, plus 1 per further asking verb joined by "en"
  ("Bereken … en leg uit …"); other sentences count 0. A non-empty task counts at least 1.
- task_form_ok(task, rules): IT8 — the task starts with an asking verb or is a direct question
- new_numbers(lead, known_texts): §3.1 numbers_lead / IT11 — the numbers in the lead (IT3 scanner: reference numbers
  are skipped; 0, 1, 100 and years are exempt) whose value is not in the intro or sources
Rules: data/toets/asking_verbs.json plus the subject overlay subjects/<s>/toets/asking_verbs.json (lists added).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
from common import DATA, ROOT, load_json  # noqa: E402
from nlnum import close, scan_numbers  # noqa: E402

ASKING_VERBS_PATH = DATA / "toets" / "asking_verbs.json"
EXEMPT = {0.0, 1.0, 100.0}
YEAR_RE = re.compile(r"^(19\d\d|20\d\d|2100)$")
SENT_SPLIT = re.compile(r"(?<=[.?!])\s+(?=[A-Z0-9À-Ý\"'‘“(€])")
WORD_RE = re.compile(r"[a-zà-ÿ]+")


def load_rules(subject: str | None = None, subjects: Path | None = None, path: Path | None = None) -> dict:
    """asking_verbs.json + the subject overlay, with compiled helper patterns."""
    base = load_json(path or ASKING_VERBS_PATH)
    verbs, helpers, joiners = list(base["verbs"]), list(base["helpers"]), list(base["joiners"])
    if subject:
        ov = (subjects or ROOT / "subjects") / subject / "toets" / "asking_verbs.json"
        if ov.exists():
            o = load_json(ov)
            verbs += [v for v in o.get("verbs", []) if v not in verbs]
            helpers += o.get("helpers", [])
            joiners += [j for j in o.get("joiners", []) if j not in joiners]
    return {"verbs": set(verbs), "helpers": [re.compile(h["pattern"], re.I) for h in helpers], "joiners": set(joiners),
            "version": base.get("version")}


def words(text: str | None) -> int:
    return len((text or "").split())


def sentences(text: str | None) -> list[str]:
    t = " ".join((text or "").split())
    return [s.strip() for s in SENT_SPLIT.split(t) if s.strip()] if t else []


def _first_word(s: str) -> str:
    m = WORD_RE.search(s.lower())
    return m.group(0) if m and s.lower().lstrip(" \"'‘“(").startswith(m.group(0)) else ""


def is_helper(sentence: str, rules: dict) -> bool:
    s = sentence.strip().lstrip(" \"'‘“(")
    return any(h.search(s) for h in rules["helpers"])


def starts_with_verb(sentence: str, rules: dict) -> bool:
    return _first_word(sentence) in rules["verbs"]


def joined_verbs(sentence: str, rules: dict) -> int:
    """Further asking verbs joined by 'en' inside one sentence: 'Bereken … en leg uit …' → 1."""
    toks = WORD_RE.findall(sentence.lower())
    return sum(1 for a, b in zip(toks, toks[1:]) if a in rules["joiners"] and b in rules["verbs"])


def sentence_tasks(sentence: str, rules: dict) -> int:
    if is_helper(sentence, rules):
        return 0
    if starts_with_verb(sentence, rules) or sentence.rstrip().endswith("?"):
        return 1 + joined_verbs(sentence, rules)
    return 0


def count_tasks(task: str | None, rules: dict) -> int:
    ss = sentences(task)
    if not ss:
        return 0
    return max(1, sum(sentence_tasks(s, rules) for s in ss))


def task_form_ok(task: str | None, rules: dict) -> bool:
    ss = sentences(task)
    return bool(ss) and any(starts_with_verb(s, rules) or s.rstrip().endswith("?") for s in ss if not is_helper(s, rules))


def _exempt(lit: str, val: float, pct: bool) -> bool:
    return val in EXEMPT or (not pct and bool(YEAR_RE.match(lit)))


def new_numbers(lead: str | None, known_texts: list[str]) -> list[str]:
    """The numbers in `lead` whose value is not in any of `known_texts` (the intro and the sources)."""
    known = [v for t in known_texts for _, v, _ in scan_numbers(t or "")]
    out = []
    for lit, val, pct in scan_numbers(lead or ""):
        if _exempt(lit, val, pct):
            continue
        if not any(close(val, k) or (pct and close(val / 100, k)) for k in known):
            out.append(lit)
    return out


def percentile(xs: list[float], q: float) -> float:
    """Linear interpolation between closest ranks (q in 0..1); [] → 0."""
    if not xs:
        return 0.0
    s = sorted(xs)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)
