#!/usr/bin/env python3
"""Run the supported SanMitra bootstrap pytest suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from supported_tests import DEFAULT_PYTEST_KEYWORD, SUPPORTED_TESTS


ROOT = Path(__file__).resolve().parents[1]


def existing_tests() -> list[str]:
    return [path for path in SUPPORTED_TESTS if (ROOT / path).exists()]


def main() -> int:
    tests = existing_tests()
    if not tests:
        print("No supported pytest files found.")
        return 0

    command = [
        sys.executable,
        "-m",
        "pytest",
        *tests,
        "-q",
        "-k",
        DEFAULT_PYTEST_KEYWORD,
    ]
    print(f"+ {' '.join(command)}")
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
