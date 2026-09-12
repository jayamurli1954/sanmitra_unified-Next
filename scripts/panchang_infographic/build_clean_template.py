"""Build a clean art+logos template from the AI reference (no Panchang text).

The AI image is a flattened bitmap — Canva cannot delete separate text layers.
This script keeps logo/art crops, then rebuilds empty content panels so no ghost
text (Onam, times, etc.) can bleed through.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

PACKAGE_DIR = Path(__file__).resolve().parent
REFERENCE = PACKAGE_DIR / "assets" / "reference_design.jpg"
OUTPUT = PACKAGE_DIR / "assets" / "template_clean.png"

W, H = 1080, 1350
CREAM = "#F3EBDD"
PANEL = "#FBF6EE"
INAUS = "#FFF3F3"
AUSP = "#F2FAF0"
VISH = "#FFF9E8"
GREEN = "#1B5E20"
GOLD = "#C8A951"


def main() -> None:
    if not REFERENCE.is_file():
        raise SystemExit(f"Missing reference: {REFERENCE}")

    src = Image.open(REFERENCE).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)

    # Tight crops — avoid AI text that sits near the diya/moon art.
    crops = {
        "logo_left": src.crop((40, 40, 230, 175)),
        "logo_right": src.crop((860, 40, 1045, 175)),
        "icons": src.crop((55, 250, 140, 700)),
        "moon": src.crop((910, 1140, 1045, 1245)),
        "border_tl": src.crop((20, 20, 110, 110)),
        "border_tr": src.crop((970, 20, 1060, 110)),
    }

    image = Image.new("RGBA", (W, H), CREAM)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((28, 28, W - 28, H - 28), radius=18, outline=GOLD, width=4)
    draw.rounded_rectangle((40, 40, W - 40, H - 40), radius=14, outline=GREEN, width=2)

    image.paste(crops["border_tl"], (20, 20), crops["border_tl"])
    image.paste(crops["border_tr"], (970, 20), crops["border_tr"])
    image.paste(crops["logo_left"], (40, 40), crops["logo_left"])
    image.paste(crops["logo_right"], (860, 40), crops["logo_right"])
    image.paste(crops["icons"], (55, 250), crops["icons"])
    image.paste(crops["moon"], (910, 1135), crops["moon"])

    # Empty panels for live text
    draw.rounded_rectangle((280, 200, 800, 236), radius=18, fill=GREEN)
    draw.rounded_rectangle((150, 250, 1020, 730), radius=16, fill=PANEL, outline="#C8E6C9", width=2)
    draw.rounded_rectangle((55, 750, 520, 980), radius=14, fill=INAUS, outline="#FFCDD2", width=2)
    draw.rounded_rectangle((540, 750, 1020, 980), radius=14, fill=AUSP, outline="#C8E6C9", width=2)
    draw.rounded_rectangle((55, 1000, 890, 1125), radius=14, fill=VISH, outline="#E0E0E0", width=2)
    draw.rectangle((0, H - 90, W, H), fill=GREEN)

    out = image.convert("RGB")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUTPUT, format="PNG", optimize=True)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
