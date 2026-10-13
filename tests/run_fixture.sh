#!/usr/bin/env bash
# Thin wrapper; the real runner is tests/run_fixture.py (works on Windows too: python tests/run_fixture.py)
cd "$(dirname "$0")/.." && exec python3 tests/run_fixture.py
