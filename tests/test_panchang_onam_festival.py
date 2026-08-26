from datetime import datetime

from app.services.panchang import PanchangService


def test_onam_thiruvonam_detected_on_2026_08_26():
    """Onam is Thiruvonam (Shravana) nakshatra in Malayalam Chingam month."""
    panchang = PanchangService().calculate_panchang(
        datetime(2026, 8, 26, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )

    assert panchang["panchang"]["nakshatra"]["name"] == "Shravana"
    festival_names = [item.get("name") for item in (panchang.get("festivals") or [])]
    assert "Onam" in festival_names

    special = panchang.get("special_notes") or {}
    assert "Onam" in (special.get("summary") or "")
    assert "Onam" in (special.get("festivals") or [])

    south = panchang.get("south_india_special") or []
    assert any("Onam" in str(item.get("english") or "") for item in south)


def test_onam_not_flagged_outside_chingam_shravana():
    panchang = PanchangService().calculate_panchang(
        datetime(2026, 5, 24, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )
    festival_names = [item.get("name") for item in (panchang.get("festivals") or [])]
    assert "Onam" not in festival_names
