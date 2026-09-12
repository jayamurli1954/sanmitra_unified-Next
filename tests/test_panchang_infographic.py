from datetime import datetime
from pathlib import Path

import pytest

from scripts.panchang_infographic.render import (
    build_text_payload,
    create_default_template,
    export_infographic,
    load_i18n,
    render_infographic_bytes,
    require_raqm,
)

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
        "tithi": {"name": "Purnima", "paksha": "Shukla", "full_name": "Shukla Purnima"},
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
            "english": "Purnima observance",
            "kannada": "ಪೌರ್ಣಿಮಾ ಆಚರಣೆ",
            "sanskrit": "पूर्णिमा पर्व",
            "text": "Purnima observance | ಪೌರ್ಣಿಮಾ ಆಚರಣೆ | पूर्णिमा पर्व",
        }
    ],
}


def test_build_text_payload_kannada_translations():
    payload = build_text_payload(SAMPLE, load_i18n())
    assert payload["tithi_kn"] == "ಶುಕ್ಲ ಪೌರ್ಣಿಮಾ"
    assert payload["nakshatra_kn"] == "ಧನಿಷ್ಠಾ"
    assert payload["vara_kn"] == "ಗುರುವಾರ"
    assert payload["samvatsara_kn"] == "ಪರಾಭವ"
    assert "ಪೌರ್ಣಿಮಾ" in payload["vishesha_1"]


@pytest.mark.skipif(not __import__("PIL").features.check("raqm"), reason="Pillow lacks libraqm")
def test_render_infographic_png_bytes():
    require_raqm()
    png = render_infographic_bytes(SAMPLE)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 5000


@pytest.mark.skipif(not __import__("PIL").features.check("raqm"), reason="Pillow lacks libraqm")
def test_export_infographic_writes_platform_sizes(tmp_path: Path):
    require_raqm()
    create_default_template(tmp_path / "template.png")
    outputs = export_infographic(
        SAMPLE,
        tmp_path / "out",
        template_path=tmp_path / "template.png",
    )
    assert set(outputs) == {"whatsapp", "instagram", "facebook"}
    assert outputs["whatsapp"].name == "panchang_whatsapp_1080x1350.png"
    assert outputs["facebook"].name == "panchang_facebook_1200x1500.png"
    assert outputs["whatsapp"].stat().st_size > 5000


def test_live_panchang_calculation_smoke():
    from app.services.panchang import PanchangService

    data = PanchangService().calculate_panchang(
        datetime(2026, 8, 27, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )
    payload = build_text_payload(data, load_i18n())
    assert payload["tithi_en"] == "Shukla Purnima"
    assert payload["title_kn"] == "ಇಂದಿನ ಪಂಚಾಂಗ"
    vishesha_blob = " ".join(payload.get(f"vishesha_{idx}", "") for idx in range(1, 4))
    assert "Onam" not in vishesha_blob
    assert "Purnima" in payload["tithi_en"] or "Purnima" in vishesha_blob
    assert payload["title_en"].endswith("Today's Panchang")
