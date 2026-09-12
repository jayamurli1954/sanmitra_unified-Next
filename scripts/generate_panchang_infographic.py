#!/usr/bin/env python3
"""Generate daily Panchang social-media infographics with shaped Kannada/Hindi text.

Examples:
  python scripts/generate_panchang_infographic.py
  python scripts/generate_panchang_infographic.py --date 2026-08-27 --city Bengaluru
  python scripts/generate_panchang_infographic.py --json tmp/panchang.json --template my_template.png
  python scripts/generate_panchang_infographic.py --write-default-template
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
from scripts.panchang_infographic.render import (  # noqa: E402
    DEFAULT_LAYOUT,
    DEFAULT_TEMPLATE,
    LEGACY_LAYOUT,
    LEGACY_TEMPLATE,
    create_branded_template,
    create_default_template,
    export_infographic,
    require_raqm,
)

DEFAULT_OUTPUT_DIR = ROOT / "tmp" / "panchang_infographic"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Panchang infographic PNGs.")
    parser.add_argument("--date", help="Gregorian date YYYY-MM-DD (default: today IST-ish via local clock)")
    parser.add_argument("--city", default="Bengaluru", help="Display city name")
    parser.add_argument("--latitude", type=float, default=12.9716)
    parser.add_argument("--longitude", type=float, default=77.5946)
    parser.add_argument("--json", dest="json_path", help="Use an existing Panchang JSON file instead of calculating")
    parser.add_argument("--template", type=Path, help="Custom template PNG (1080x1350 recommended)")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT, help="Layout/coordinate JSON")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prefix", default="panchang", help="Output filename prefix")
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Use the simple plain template instead of the branded reference artwork",
    )
    parser.add_argument(
        "--write-default-template",
        action="store_true",
        help="Write the branded template PNG (from reference artwork) and exit",
    )
    return parser.parse_args()


def _load_data(args: argparse.Namespace) -> dict:
    if args.json_path:
        return json.loads(Path(args.json_path).read_text(encoding="utf-8"))
    when = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    service = PanchangService()
    return service.calculate_panchang(when, args.latitude, args.longitude, args.city)


def main() -> int:
    args = _parse_args()
    require_raqm()

    layout_path = LEGACY_LAYOUT if args.plain else args.layout
    template_path = args.template
    if args.plain and not template_path:
        template_path = LEGACY_TEMPLATE

    if args.write_default_template:
        if args.plain:
            path = create_default_template(
                LEGACY_TEMPLATE,
                json.loads(LEGACY_LAYOUT.read_text(encoding="utf-8")),
                plain=True,
            )
        else:
            path = create_branded_template(
                DEFAULT_TEMPLATE,
                json.loads(DEFAULT_LAYOUT.read_text(encoding="utf-8")),
            )
        print(f"Wrote template: {path}")
        return 0

    data = _load_data(args)
    outputs = export_infographic(
        data,
        args.output_dir,
        template_path=template_path,
        layout_path=layout_path,
        prefix=args.prefix,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
