"""Shared helpers for the leerdoel-straat validators."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMAS = ROOT / "schemas"

BLOOM_ORDER = ["onthouden", "begrijpen", "toepassen", "analyseren", "evalueren", "creëren"]


def load_json(path: str | Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def bloom_rank(level: str) -> int:
    return BLOOM_ORDER.index(level)


def normalise_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("­", "")).strip().lower()


def validate_schema(data, schema_name: str) -> list[str]:
    """Return a list of schema error messages (empty when valid)."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return ["jsonschema not installed: pip install jsonschema"]
    schema = load_json(SCHEMAS / schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))]


class Report:
    """Collects findings with severity; exit code 1 on any 'fail'."""

    def __init__(self, name: str):
        self.name = name
        self.items: list[tuple[str, str, str]] = []  # (severity, rule, message)

    def fail(self, rule: str, msg: str) -> None:
        self.items.append(("fail", rule, msg))

    def warn(self, rule: str, msg: str) -> None:
        self.items.append(("warn", rule, msg))

    def info(self, rule: str, msg: str) -> None:
        self.items.append(("info", rule, msg))

    @property
    def failed(self) -> bool:
        return any(s == "fail" for s, _, _ in self.items)

    def print_and_exit(self, json_out: str | None = None) -> None:
        counts = {s: sum(1 for x in self.items if x[0] == s) for s in ("fail", "warn", "info")}
        print(f"[{self.name}] fail={counts['fail']} warn={counts['warn']} info={counts['info']}")
        for sev, rule, msg in self.items:
            print(f"  {sev.upper():5} {rule:4} {msg}")
        if json_out:
            save_json(json_out, {"name": self.name, "failed": self.failed,
                                 "items": [{"severity": s, "rule": r, "message": m} for s, r, m in self.items]})
        sys.exit(1 if self.failed else 0)
