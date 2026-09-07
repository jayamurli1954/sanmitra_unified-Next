from datetime import datetime
from pathlib import Path

import pytest

from scripts.panchang_card.card_data import build_card_context
from scripts.panchang_card.render import render_html, write_rendered_html


SAMPLE = {
    "date": {
        "gregorian": {
            "date": "2026-08-27",
            "day": "Thursday",
            "formatted": "Thursday, 27 August, 2026",
        },
        "hindu": {
            "month": "Bhadrapada",
            "paksha": "Shukla",
            "samvatsara_name": "Parabhava",
        },
    },
    "location": {"city": "Bengaluru"},
    "ayana": "Dakshinayana",
    "panchang": {
        "tithi": {"name": "Purnima", "paksha": "Shukla"},
        "nakshatra": {"name": "Dhanishta"},
        "yoga": {"name": "Atiganda"},
        "karana": {"current": "Vishti"},
        "vara": {"name": "Thursday", "sanskrit": "गुरुवार"},
    },
    "inauspicious_times": {
        "rahu_kaal": {"start": "13:30:00", "end": "15:00:00"},
        "yamaganda": {"start": "06:00:00", "end": "07:30:00"},
        "gulika": {"start": "12:00:00", "end": "13:30:00"},
    },
    "additional_inauspicious_times": {
        "dur_muhurta": [{"start": "12:24:00", "end": "13:12:00"}],
        "varjyam": [{"start": "08:07:00", "end": "09:46:00"}],
    },
    "auspicious_times": {
        "abhijit_muhurat": {"start": "11:48:00", "end": "12:36:00"},
        "brahma_muhurat": {"start": "04:30:00", "end": "05:18:00"},
        "amrita_kalam": {"start": "07:10:00", "end": "08:50:00"},
    },
    "south_india_special": [
        {
            "english": "Purnima Observance",
            "kannada": "ಪೌರ್ಣಿಮಾ ಆಚರಣೆ",
            "sanskrit": "पूर्णिमा पर्व",
        }
    ],
}


def test_build_card_context_translations():
    ctx = build_card_context(SAMPLE)
    assert ctx["title_kn"] == "ಇಂದಿನ ಪಂಚಾಂಗ"
    tithi = next(row for row in ctx["rows"] if row["label"] == "Tithi")
    assert tithi["kn"] == "ಶುಕ್ಲ ಪೌರ್ಣಿಮಾ"
    assert tithi["en"] == "Shukla Purnima"
    assert "Onam" not in str(ctx)
    assert ctx["vishesha"][0]["en"] == "Purnima Observance"
    assert ctx["vishesha"][0]["kn"] == "ಪೌರ್ಣಿಮಾ ಆಚರಣೆ"
    assert "ಪೂರ್ಣಿಮಾ" not in tithi["kn"]
    assert "ಪೂರ್ಣಿಮಾ" not in ctx["vishesha"][0]["kn"]
    assert ctx["logo_mandirmitra_uri"]
    assert ctx["logo_sanmitra_uri"]
    assert ctx["frame_svg_uri"]
    assert ctx["frame_svg_uri"].endswith("frame.svg")


def test_render_html_contains_shaped_scripts(tmp_path: Path):
    ctx = build_card_context(SAMPLE)
    html = render_html(ctx)
    assert "ಶುಕ್ಲ ಪೌರ್ಣಿಮಾ" in html
    assert "ಪೌರ್ಣಿಮಾ ಆಚರಣೆ" in html
    assert "शुक्ल पूर्णिमा" in html
    assert "NotoSansKannada" in html
    assert "frame.svg" in html
    assert "mandirmitra.png" in html or "mandirmitra.svg" in html
    path = write_rendered_html(ctx, tmp_path / "card.html")
    assert path.is_file()


def test_live_panchang_card_context_no_onam_on_aug_27():
    from app.services.panchang import PanchangService

    data = PanchangService().calculate_panchang(
        datetime(2026, 8, 27, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )
    ctx = build_card_context(data)
    blob = str(ctx)
    assert "Onam" not in blob
    tithi = next(row for row in ctx["rows"] if row["label"] == "Tithi")
    assert "Purnima" in tithi["en"]


def _playwright_chromium_available() -> bool:
    if __import__("importlib").util.find_spec("playwright") is None:
        return False
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            return Path(playwright.chromium.executable_path).is_file()
    except Exception:
        return False


@pytest.mark.skipif(
    not _playwright_chromium_available(),
    reason="playwright chromium browser is not installed",
)
def test_export_card_png_smoke(tmp_path: Path):
    from scripts.panchang_card.render import export_card_pngs

    outputs = export_card_pngs(SAMPLE, tmp_path / "out", keep_html=True)
    assert outputs["whatsapp"].is_file()
    assert outputs["whatsapp"].stat().st_size > 5000
    assert outputs["facebook"].is_file()
