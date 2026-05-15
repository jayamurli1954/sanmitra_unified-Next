from __future__ import annotations

import csv
from pathlib import Path


def _to_int(value: str) -> int:
    text = (value or "").strip().lower()
    if text in {"1", "yes", "y", "true"}:
        return 1
    return 0


def main() -> None:
    csv_path = Path("docs/multica_pilot_scorecard.csv")
    if not csv_path.exists():
        raise SystemExit("Scorecard not found: docs/multica_pilot_scorecard.csv")

    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8", newline="")))
    if not rows:
        raise SystemExit("Scorecard is empty.")

    total = len(rows)
    useful = sum(_to_int(r.get("useful", "")) for r in rows)
    noise = sum(_to_int(r.get("noise", "")) for r in rows)
    regressions = sum(_to_int(r.get("regression", "")) for r in rows)
    wrong_scope = sum(_to_int(r.get("wrong_scope", "")) for r in rows)

    rework_minutes = sum(int((r.get("rework_minutes", "0") or "0").strip() or "0") for r in rows)
    median_like = rework_minutes / total

    useful_rate = 100.0 * useful / total
    regression_rate = 100.0 * regressions / total
    wrong_scope_rate = 100.0 * wrong_scope / total

    print("Multica Pilot Summary")
    print(f"Tasks: {total}")
    print(f"Useful output rate: {useful_rate:.1f}%")
    print(f"Noise count: {noise}")
    print(f"Regression rate: {regression_rate:.1f}%")
    print(f"Wrong-scope rate: {wrong_scope_rate:.1f}%")
    print(f"Avg review+rework time: {median_like:.1f} min/task")
    print("")
    print("Threshold check (target):")
    print(f"- Useful >= 65%: {'PASS' if useful_rate >= 65 else 'FAIL'}")
    print(f"- Regression <= 10%: {'PASS' if regression_rate <= 10 else 'FAIL'}")
    print(f"- Wrong-scope <= 15%: {'PASS' if wrong_scope_rate <= 15 else 'FAIL'}")
    print(f"- Avg review+rework <= 25 min: {'PASS' if median_like <= 25 else 'FAIL'}")


if __name__ == "__main__":
    main()
