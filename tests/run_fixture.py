#!/usr/bin/env python3
"""Exercise every script on the synthetic fixture (cross-platform; no bash needed).

Usage: python tests/run_fixture.py
Copies the fixture to a temp dir so the fixture itself stays clean. Exit code 1 on any failure.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
PY = sys.executable


def run(label: str, *args: str, allow_fail: bool = False) -> bool:
    print(f"== {label}")
    r = subprocess.run([PY, *args], cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
    print(r.stdout, end="")
    if r.returncode != 0 and not allow_fail:
        print(r.stderr, end="")
        print(f"!! FAILED: {label}")
        return False
    if r.returncode != 0:
        print("(non-zero exit expected here)")
    return True


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    r = tmp / "run"
    shutil.copytree(ROOT / "tests" / "fixtures" / "run", r)
    (r / "04_groups_student.template.json").rename(r / "04_groups_student.json")
    (r / "05_verification.round1.template.json").rename(r / "05_verification.round1.json")
    s = "scripts"
    ok = True
    ok &= run("decisions snapshot", f"{s}/decisions.py", "snapshot", "economie", str(r))
    ok &= run("validate source_units", f"{s}/validate.py", "source_units", f"{r}/01_source_units.json")
    ok &= run("validate plan", f"{s}/validate.py", "plan", f"{r}/02_plan.json", f"{r}/01_source_units.json")
    ok &= run("merge", f"{s}/merge_groups.py", str(r))
    ok &= run("validate groups", f"{s}/validate.py", "groups", f"{r}/03_groups_raw.json", f"{r}/01_source_units.json", f"{r}/02_plan.json")
    ok &= run("bloom_check --write", f"{s}/bloom_check.py", f"{r}/03_groups_raw.json", f"{r}/02_plan.json", "--write")
    ok &= run("student_language_check", f"{s}/student_language_check.py", f"{r}/04_groups_student.json", f"{r}/03_groups_raw.json")
    ok &= run("coverage", f"{s}/coverage.py", f"{r}/01_source_units.json", f"{r}/04_groups_student.json", f"{r}/02_plan.json", "--out", f"{r}/coverage.json")
    ok &= run("validate verification", f"{s}/validate.py", "verification", f"{r}/05_verification.round1.json", f"{r}/04_groups_student.json")
    ok &= run("apply_verdicts (repair expected)", f"{s}/apply_verdicts.py", str(r), "1", allow_fail=True)
    ok &= run("export", f"{s}/export.py", str(r))
    print()
    print("Output in", r / "output", ":", sorted(p.name for p in (r / "output").iterdir()))
    print("\nRESULT:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
