#!/usr/bin/env python3
"""File-size guard — keep source files small so the codebase stays maintainable.

Why: a code review found 30+ source files over 1,000 lines (one over 20,000). Large
files are hard to read, review, and change safely. This guard stops the problem from
getting worse while we split the existing offenders (see
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md).

How it works (a one-way ratchet):
  * WARN_LIMIT (800)  : files above this print a warning. Informational; never fails.
  * FAIL_LIMIT (1500) : a NEW file above this fails the check.
  * baseline          : the existing offenders are grandfathered in
                        scripts/file_size_baseline.json with their CURRENT line count as
                        a ceiling. A grandfathered file FAILS only if it grows ABOVE its
                        recorded ceiling. As you split a file below its ceiling, re-run
                        with --update-baseline to lock in the gain (the ceiling can only
                        go down, never up, unless you deliberately re-baseline).

So: new giant files are blocked immediately, and the existing giants can only shrink.

Usage:
    python scripts/check_file_size.py                 # check (used by preflight)
    python scripts/check_file_size.py --update-baseline  # re-record ceilings (deliberate)
    python scripts/check_file_size.py --list             # show current offenders, sorted

Exit code is non-zero if any file violates the ratchet, so it is safe to chain in CI.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "scripts" / "file_size_baseline.json"

WARN_LIMIT = 800
FAIL_LIMIT = 1500

# Only these extensions count as "source we want to keep small".
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".vue"}

# Path fragments to skip (vendored / generated / minified). git ls-files already
# excludes anything gitignored (node_modules, build output, .venv, etc.).
EXCLUDE_FRAGMENTS = (
    "node_modules/",
    "external-repos/",
    "/dist/",
    "/build/",
    ".min.",
    "-min.",
    "vendor/",
)


def tracked_source_files() -> list[str]:
    # Tracked/staged files, plus untracked files that are NOT gitignored, so a brand-new
    # oversized file is caught even before it is `git add`ed.
    seen: set[str] = set()
    for args in (["git", "ls-files"],
                 ["git", "ls-files", "--others", "--exclude-standard"]):
        out = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout
        for line in out.splitlines():
            path = line.strip()
            if not path:
                continue
            if Path(path).suffix.lower() not in SOURCE_SUFFIXES:
                continue
            posix = path.replace("\\", "/")
            if any(frag in posix for frag in EXCLUDE_FRAGMENTS):
                continue
            seen.add(posix)
    return sorted(seen)


def count_lines(path: str) -> int:
    full = ROOT / path
    try:
        with full.open("r", encoding="utf-8", errors="ignore") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def load_baseline() -> dict[str, int]:
    if not BASELINE_PATH.exists():
        return {}
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def measure() -> dict[str, int]:
    return {path: count_lines(path) for path in tracked_source_files()}


def update_baseline() -> int:
    sizes = measure()
    offenders = {p: n for p, n in sizes.items() if n > WARN_LIMIT}
    ordered = dict(sorted(offenders.items(), key=lambda kv: (-kv[1], kv[0])))
    BASELINE_PATH.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote baseline with {len(ordered)} grandfathered file(s) (> {WARN_LIMIT} lines).")
    print(f"  -> {BASELINE_PATH.relative_to(ROOT)}")
    return 0


def list_offenders() -> int:
    sizes = measure()
    offenders = sorted(
        ((n, p) for p, n in sizes.items() if n > WARN_LIMIT), reverse=True
    )
    if not offenders:
        print(f"No files over {WARN_LIMIT} lines.")
        return 0
    print(f"Files over {WARN_LIMIT} lines ({len(offenders)}):")
    for n, p in offenders:
        print(f"  {n:>6}  {p}")
    return 0


def check() -> int:
    sizes = measure()
    baseline = load_baseline()

    failures: list[str] = []
    warnings: list[str] = []
    shrunk: list[str] = []

    for path, lines in sizes.items():
        ceiling = baseline.get(path)
        if lines > FAIL_LIMIT:
            if ceiling is None:
                failures.append(
                    f"  {lines:>6}  {path}  (NEW file over hard limit {FAIL_LIMIT}; split it)"
                )
            elif lines > ceiling:
                failures.append(
                    f"  {lines:>6}  {path}  (grew beyond grandfathered ceiling {ceiling})"
                )
            # else: grandfathered and not grown -> allowed
        elif lines > WARN_LIMIT:
            if ceiling is not None and lines > ceiling:
                failures.append(
                    f"  {lines:>6}  {path}  (grew beyond grandfathered ceiling {ceiling})"
                )
            else:
                warnings.append(f"  {lines:>6}  {path}")

        # A grandfathered file that has dropped below its ceiling -> gain to lock in.
        if ceiling is not None and lines < ceiling:
            shrunk.append(f"  {path}: {ceiling} -> {lines}")

    if warnings:
        print(f"\nWARN: {len(warnings)} file(s) over {WARN_LIMIT} lines (consider splitting):")
        print("\n".join(warnings))

    if shrunk:
        print(f"\nGains detected ({len(shrunk)} grandfathered file(s) shrank). "
              f"Run `python scripts/check_file_size.py --update-baseline` to lock them in:")
        print("\n".join(shrunk))

    if failures:
        print(f"\nFAIL: {len(failures)} file-size violation(s):")
        print("\n".join(failures))
        print("\nFix by splitting the file (see docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md), "
              "or, if this is a deliberate re-baseline, run --update-baseline.")
        return 1

    print(f"\nfile-size guard OK (hard limit {FAIL_LIMIT}, warn {WARN_LIMIT}, "
          f"{len(baseline)} grandfathered).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guard against oversized source files.")
    parser.add_argument("--update-baseline", action="store_true",
                        help="Re-record current offenders as grandfathered ceilings.")
    parser.add_argument("--list", action="store_true",
                        help="List files over the warn limit and exit.")
    args = parser.parse_args()

    if args.update_baseline:
        return update_baseline()
    if args.list:
        return list_offenders()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
