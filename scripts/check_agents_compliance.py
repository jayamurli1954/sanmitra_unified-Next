#!/usr/bin/env python3
"""Check that AGENTS.md acceptance policy remains wired into CI gates."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_AGENTS_MARKERS = (
    "## 25. PR Acceptance Checklist",
    "tenant isolation",
    "app-key",
    "module access",
    "accounting invariants",
    "cross-database",
    "current state",
    "target state",
    "rollback",
    "tests",
)

REQUIRED_CI_MARKERS = {
    ".github/workflows/ci.yml": "python scripts/check_agents_compliance.py",
    ".github/workflows/accounting-stability-gate.yml": "python scripts/check_agents_compliance.py",
    "scripts/release_preflight.py": "scripts/check_agents_compliance.py",
}


def read_text(path: Path) -> str:
    if not path.exists():
        print(f"Missing required file: {path.relative_to(ROOT)}")
        raise SystemExit(1)
    return path.read_text(encoding="utf-8")


def main() -> int:
    violations: list[str] = []
    agents_text = read_text(ROOT / "AGENTS.md").lower()

    for marker in REQUIRED_AGENTS_MARKERS:
        if marker.lower() not in agents_text:
            violations.append(f"AGENTS.md is missing marker: {marker}")

    for rel_path, marker in REQUIRED_CI_MARKERS.items():
        text = read_text(ROOT / rel_path)
        if marker not in text:
            violations.append(f"{rel_path} does not run {marker}")

    if violations:
        print("AGENTS compliance check failed:")
        for violation in violations:
            print(f" - {violation}")
        return 1

    print("AGENTS compliance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

