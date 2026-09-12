#!/usr/bin/env python3
"""Generate MandirMitra daily Panchang social cards via HTML + Playwright.

Examples:
  python scripts/generate_panchang_card.py
  python scripts/generate_panchang_card.py --date 2026-08-27 --city Bengaluru
  python scripts/generate_panchang_card.py --json tmp/panchang.json --keep-html
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.panchang import PanchangService  # noqa: E402
from scripts.panchang_card.render import export_card_pngs  # noqa: E402

DEFAULT_OUTPUT_DIR = ROOT / "tmp" / "panchang_card"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate MandirMitra Panchang HTML→PNG cards.")
    parser.add_argument("--date", help="Gregorian date YYYY-MM-DD (default: today local noon)")
    parser.add_argument("--city", default="Bengaluru")
    parser.add_argument("--latitude", type=float, default=12.9716)
    parser.add_argument("--longitude", type=float, default=77.5946)
    parser.add_argument("--json", dest="json_path", help="Use existing Panchang JSON instead of calculating")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prefix", help="Output filename prefix (default: panchang_YYYY_MM_DD)")
    parser.add_argument("--keep-html", action="store_true", help="Keep rendered HTML alongside PNGs")
    return parser.parse_args()


def _load_data(args: argparse.Namespace) -> dict:
    if args.json_path:
        return json.loads(Path(args.json_path).read_text(encoding="utf-8"))
    when = (
        datetime.strptime(args.date, "%Y-%m-%d").replace(hour=12, minute=0, second=0, microsecond=0)
        if args.date
        else datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    )
    return PanchangService().calculate_panchang(when, args.latitude, args.longitude, args.city)


def main() -> int:
    args = _parse_args()
    data = _load_data(args)
    outputs = export_card_pngs(
        data,
        args.output_dir,
        prefix=args.prefix,
        keep_html=args.keep_html,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
