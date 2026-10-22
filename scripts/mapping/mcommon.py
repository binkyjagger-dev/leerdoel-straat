"""Shared helpers for the methode-straat (mapping) scripts. Imports the leerdoel-straat common module."""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import ROOT, Report, load_json, save_json, validate_schema  # noqa: E402,F401

MAX_QUOTE_WORDS = 25
GRADATIONS = ["leert", "herhaalt", "oefent", "noemt"]
TREATMENTS = ["explains", "practises", "mentions", "none"]

STOP = set("""de het een en of van in op te is zijn wordt worden bij voor met aan als dat die dit er niet
ook naar door uit om over tot dan nog zo al maar hoe wat welke waarbij waarin kan kunnen ik je hij zij
we wij ze hun haar zijn mijn deze dus per dan meer minder dat""".split())


def norm(s: str) -> str:
    """Lower-case, strip accents, collapse whitespace and punctuation to single spaces."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"[^\w\s%€]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str) -> list[str]:
    return [t for t in norm(s).split() if t not in STOP and len(t) > 2]


def stem(t: str) -> str:
    """Very light Dutch stemmer: strip common plural/inflection endings."""
    for suf in ("heden", "ingen", "eren", "en", "s", "e"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)]
    return t


def stems(s: str) -> set[str]:
    return {stem(t) for t in tokens(s)}


def read_text(run_dir: Path, ref: str | None) -> str:
    if not ref:
        return ""
    p = run_dir / ref
    return p.read_text(encoding="utf-8") if p.exists() else ""


def words(s: str) -> int:
    return len(s.split())


def levenshtein_ratio(a: str, b: str) -> float:
    """1 - edit distance / max(len). Small inputs only (quote windows)."""
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return 1 - prev[lb] / max(la, lb)


def quote_in_text(quote: str, text: str, tolerant: bool = False) -> tuple[bool, float]:
    """Verbatim (whitespace-insensitive) match, or OCR-tolerant window match at >= 95 % similarity."""
    q, t = norm(quote), norm(text)
    if not q:
        return False, 0.0
    if q in t:
        return True, 1.0
    if not tolerant:
        return False, 0.0
    n = len(q)
    best = 0.0
    step = max(1, n // 8)
    for i in range(0, max(1, len(t) - n + 1), step):
        r = levenshtein_ratio(q, t[i:i + n])
        if r > best:
            best = r
            if best >= 0.95:
                break
    return best >= 0.95, best
