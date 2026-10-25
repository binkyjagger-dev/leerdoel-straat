#!/usr/bin/env python3
"""Exercise the methode-straat scripts on the koppel fixture. Usage: python tests/run_koppel_fixture.py"""
from __future__ import annotations
import shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
PY = sys.executable
def run(label, *args, allow_fail=False):
    print(f"== {label}")
    r = subprocess.run([PY, *args], cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
    print(r.stdout, end="")
    if r.returncode != 0 and not allow_fail:
        print(r.stderr, end=""); print(f"!! FAILED: {label}"); return False
    return True
def main():
    r = Path(tempfile.mkdtemp()) / "run"; shutil.copytree(ROOT / "tests" / "fixtures" / "koppel", r)
    s = "scripts/mapping"; ok = True
    ok &= run("validate_method", f"{s}/validate_method.py", str(r))
    ok &= run("candidates", f"{s}/candidates.py", str(r))
    ok &= run("gradation", f"{s}/gradation.py", str(r))
    ok &= run("check_mappings", f"{s}/check_mappings.py", str(r))
    ok &= run("check_mappings --verification", f"{s}/check_mappings.py", str(r), "--verification", "15_verification.json")
    ok &= run("export", f"{s}/export_mappings.py", str(r))
    ok &= run("compare_baseline", f"{s}/compare_baseline.py", str(r), str(r / "baseline.csv"))
    # part B
    ok &= run("ex_candidates", f"{s}/ex_candidates.py", str(r))
    ok &= run("ex_merge", f"{s}/ex_merge.py", str(r))
    ok &= run("check_ex_mappings", f"{s}/check_ex_mappings.py", str(r))
    ok &= run("check_ex_mappings --verification", f"{s}/check_ex_mappings.py", str(r), "--verification", "19_ex_verification.json")
    ok &= run("check_ex_mappings --verification (again, idempotent)", f"{s}/check_ex_mappings.py", str(r), "--verification", "19_ex_verification.json")
    shutil.copytree(r / "_repair" / "18_ex_judgements.R", r / "18_ex_judgements.R")
    ok &= run("ex_merge (with repair R)", f"{s}/ex_merge.py", str(r))
    ok &= run("check_ex_mappings --verification (after repair)", f"{s}/check_ex_mappings.py", str(r), "--verification", "19_ex_verification.json")
    ok &= run("export_exercises", f"{s}/export_exercises.py", str(r))
    ok &= run("export (after part B)", f"{s}/export_mappings.py", str(r))
    print("\nOutput:", sorted(p.name for p in (r / "output").iterdir()))
    print("\nRESULT:", "OK" if ok else "FAILED"); return 0 if ok else 1
if __name__ == "__main__": sys.exit(main())
