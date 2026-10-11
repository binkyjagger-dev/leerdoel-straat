#!/usr/bin/env bash
# Exercises every script on the synthetic fixture. Copies the fixture to a temp run dir so the fixture stays clean.
set -euo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
cp -r tests/fixtures/run "$TMP/run"
R="$TMP/run"
mv "$R/04_groups_student.template.json" "$R/04_groups_student.json"
mv "$R/05_verification.round1.template.json" "$R/05_verification.round1.json"
S=scripts
echo "== validate source_units";  python3 $S/validate.py source_units $R/01_source_units.json
echo "== validate plan";          python3 $S/validate.py plan $R/02_plan.json $R/01_source_units.json
echo "== merge";                  python3 $S/merge_groups.py $R
echo "== validate groups";        python3 $S/validate.py groups $R/03_groups_raw.json $R/01_source_units.json $R/02_plan.json
echo "== bloom_check --write";    python3 $S/bloom_check.py $R/03_groups_raw.json $R/02_plan.json --write
echo "== student_language_check"; python3 $S/student_language_check.py $R/04_groups_student.json $R/03_groups_raw.json
echo "== coverage";               python3 $S/coverage.py $R/01_source_units.json $R/04_groups_student.json $R/02_plan.json --out $R/coverage.json
echo "== validate verification";  python3 $S/validate.py verification $R/05_verification.round1.json $R/04_groups_student.json
echo "== apply_verdicts";         python3 $S/apply_verdicts.py $R 1 || echo "(repair needed — expected for fixture)"
echo "== export";                 python3 $S/export.py $R
echo
echo "Output in $R/output:"; ls "$R/output"
echo; head -3 "$R/output/leerdoelgroepen.csv"; echo; cat "$R/output/doubt_list.md"
