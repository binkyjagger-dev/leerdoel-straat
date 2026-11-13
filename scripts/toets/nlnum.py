"""Dutch number notation, the safe calculation evaluator and the number scanner (specs/34 §3: IT3, CC).

- parse_nl("1.250,50") → 1250.5; "9%" → 9.0 (the % sign is kept apart, see scan_numbers)
- format_nl(1250.5, 2) → "1.250,50"; with prefix "€ " / suffix "%" as the shown string has them
- safe_eval(expr, names): Python `ast`, only numbers, names, + - * / ** ( ), unary minus, and min, max, round, abs,
  sum; nothing else (no attributes, subscripts, comprehensions or other calls)
- round_mode(x, digits, mode): half_up (default, as on paper), up, down — on Decimal, so 2,675 → 2,68
- scan_numbers(text): every number in Dutch notation with its position; reference numbers ("informatiebron 2",
  "vraag 3 en 4", "figuur 1", "tabel 2", "opgave 1") are skipped
"""
from __future__ import annotations

import ast
import math
import re
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

NUM_RE = re.compile(r"(?<![\w.,])-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?(?![\w])(\s?%)?")
REF_RE = re.compile(r"\b(?:informatiebron(?:nen)?|bron(?:nen)?|vraag|vragen|figuur|figuren|tabel|tabellen|opgave|opgaven)"
                    r"\s+\d+(?:\s*(?:,|en|t/m|tot en met)\s*\d+)*", re.I)
FUNCS = {"min": min, "max": max, "round": round, "abs": abs, "sum": lambda *a: sum(a[0]) if len(a) == 1 else sum(a)}


def parse_nl(s: str) -> float:
    s = s.strip().replace("€", "").replace("%", "").replace(" ", "").replace(" ", "")
    neg = s.startswith("-") or s.startswith("−")
    s = s.lstrip("-−")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?|\d+(,\d+)?", s):
        v = float(s.replace(".", "").replace(",", "."))
        return -v if neg else v
    raise ValueError(f"not a Dutch number: {s!r}")


def format_nl(x: float, digits: int | None) -> str:
    if digits is None:
        s = repr(float(x))
        if "e" in s or "E" in s:
            s = f"{x:f}"
        whole, _, frac = s.partition(".")
        frac = frac.rstrip("0")
    else:
        s = f"{abs(x):.{digits}f}"
        whole, _, frac = s.partition(".")
        whole = ("-" if x < 0 and float(s) != 0 else "") + whole
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return sign + ".".join(groups) + ("," + frac if frac else "")


def round_mode(x: float, digits: int | None, mode: str | None) -> float:
    if digits is None:
        return x
    q = Decimal(1).scaleb(-digits)
    rm = {"up": ROUND_CEILING, "down": ROUND_FLOOR}.get(mode or "half_up", ROUND_HALF_UP)
    return float(Decimal(repr(x)).quantize(q, rounding=rm))


def shown_value(shown: str) -> tuple[float, str, str, int]:
    """'€ 1.250,50' → (1250.5, '€ ', '', 2); '9,5%' → (9.5, '', '%', 1)."""
    s = shown.strip()
    prefix = "€ " if s.startswith("€") else ""
    suffix = "%" if s.endswith("%") else ""
    core = s.replace("€", "").replace("%", "").strip()
    v = parse_nl(core)
    digits = len(core.split(",", 1)[1]) if "," in core else 0
    return v, prefix, suffix, digits


class EvalError(Exception):
    pass


def safe_eval(expr: str, names: dict[str, float]) -> float:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise EvalError(f"syntax error in '{expr}': {e.msg}")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.Name):
            if n.id not in names:
                raise EvalError(f"unknown name '{n.id}'")
            return names[n.id]
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                if b == 0:
                    raise EvalError("division by zero")
                return a / b
            if abs(b) > 100:
                raise EvalError("exponent too large")
            return a ** b
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS and not n.keywords:
            args = [ev(a) for a in n.args]
            if n.func.id == "round":
                return round_mode(args[0], int(args[1]) if len(args) > 1 else 0, "half_up")
            return FUNCS[n.func.id](*args)
        if isinstance(n, (ast.List, ast.Tuple)):
            return [ev(e) for e in n.elts]
        raise EvalError(f"not allowed in a calculation: {ast.dump(n)[:60]}")

    v = ev(tree)
    if isinstance(v, list) or not math.isfinite(v):
        raise EvalError(f"'{expr}' does not give one finite number")
    return float(v)


def names_in(expr: str) -> set[str]:
    try:
        return {n.id for n in ast.walk(ast.parse(expr, mode="eval")) if isinstance(n, ast.Name)} - set(FUNCS)
    except SyntaxError:
        return set()


def scan_numbers(text: str) -> list[tuple[str, float, bool]]:
    """[(literal, value, is_percent)] for every number in the text, reference numbers skipped."""
    masked = REF_RE.sub(lambda m: " " * len(m.group(0)), text or "")
    out = []
    for m in NUM_RE.finditer(masked):
        lit = m.group(0)
        try:
            out.append((lit.strip(), parse_nl(lit.replace("%", "")), bool(m.group(1))))
        except ValueError:
            continue
    return out


def close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
