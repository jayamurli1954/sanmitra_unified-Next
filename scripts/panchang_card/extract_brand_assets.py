"""Extract MandirMitra / SanMitra logos (and optional art) from the AI reference image."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "panchang_infographic" / "assets" / "reference_design.jpg"
LOGO_DIR = Path(__file__).resolve().parent / "logos"
ART_DIR = Path(__file__).resolve().parent / "artwork"


def main() -> None:
    if not REFERENCE.is_file():
        raise SystemExit(f"Missing reference: {REFERENCE}")

    # Crops are in the reference's native pixel space (682×1024).
    src = Image.open(REFERENCE).convert("RGBA")
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)

    crops = {
        LOGO_DIR / "mandirmitra.png": (18, 18, 145, 125),
        # Icon only — template supplies "SanMitra Tech" wordmark.
        LOGO_DIR / "sanmitra.png": (560, 22, 650, 95),
        ART_DIR / "diya.png": (375, 745, 555, 845),
        ART_DIR / "moon.png": (495, 855, 655, 980),
    }
    for path, box in crops.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        src.crop(box).save(path, format="PNG")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
