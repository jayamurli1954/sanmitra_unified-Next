from datetime import datetime

from app.services.panchang import PanchangService
from app.services.panchang.festivals import (
    MAJOR_FESTIVAL_CATALOG,
    detect_day_festivals,
    match_major_festivals,
)


def _names(panchang):
    return [item.get("name") for item in (panchang.get("festivals") or [])]


def test_ganesh_chaturthi_detected_on_2026_09_14():
    panchang = PanchangService().calculate_panchang(
        datetime(2026, 9, 14, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )
    assert panchang["date"]["hindu"]["month"] == "Bhadrapada"
    assert panchang["panchang"]["tithi"]["full_name"] == "Shukla Chaturthi"
    assert "Ganesh Chaturthi" in _names(panchang)
    south = panchang.get("south_india_special") or []
    assert any("Ganesh Chaturthi" in str(item.get("english") or "") for item in south)


def test_ganesh_chaturthi_not_flagged_on_other_shukla_chaturthi():
    panchang = PanchangService().calculate_panchang(
        datetime(2026, 8, 16, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )
    assert panchang["panchang"]["tithi"]["full_name"] == "Shukla Chaturthi"
    assert panchang["date"]["hindu"]["month"] == "Shravana"
    assert "Ganesh Chaturthi" not in _names(panchang)


def test_onam_still_detected_on_2026_08_26():
    panchang = PanchangService().calculate_panchang(
        datetime(2026, 8, 26, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )
    assert "Onam" in _names(panchang)


def test_catalog_covers_requested_major_festival_names():
    names = {entry["name"] for entry in MAJOR_FESTIVAL_CATALOG}
    for required in {
        "Ugadi / Gudi Padwa",
        "Rama Navami",
        "Akshaya Tritiya",
        "Guru Purnima",
        "Naga Panchami",
        "Raksha Bandhan",
        "Krishna Janmashtami",
        "Ganesh Chaturthi",
        "Sharada Navaratri Begins",
        "Vijayadashami (Dussehra)",
        "Deepavali (Lakshmi Puja)",
        "Maha Shivaratri",
        "Holi",
        "Makar Sankranti",
        "Onam",
    }:
        assert required in names


def test_janmashtami_rule_matches_amanta_or_purnimanta_month():
    """Same lunar day: Amanta Shravana or Purnimanta Bhadrapada."""
    hit_amanta = match_major_festivals(
        tithi_name="Ashtami",
        paksha="Krishna",
        lunar_month="Shravana",
        lunar_month_purnimanta="Bhadrapada",
        nakshatra_name="Rohini",
    )
    assert any(item["name"] == "Krishna Janmashtami" for item in hit_amanta)

    hit_purnimanta_only = match_major_festivals(
        tithi_name="Ashtami",
        paksha="Krishna",
        lunar_month="Ashadha",
        lunar_month_purnimanta="Bhadrapada",
        nakshatra_name="Rohini",
    )
    assert any(item["name"] == "Krishna Janmashtami" for item in hit_purnimanta_only)

    # Amanta Ashadha Krishna Ashtami must NOT fire just because purnimanta is Shravana.
    early = match_major_festivals(
        tithi_name="Ashtami",
        paksha="Krishna",
        lunar_month="Ashadha",
        lunar_month_purnimanta="Shravana",
        nakshatra_name="Bharani",
    )
    assert all(item["name"] != "Krishna Janmashtami" for item in early)


def test_ugadi_and_chaitra_navaratri_share_pratipada():
    festivals = detect_day_festivals(
        tithi_data={"name": "Pratipada", "paksha": "Shukla", "number": 1},
        nakshatra={"name": "Revati"},
        lunar_month="Chaitra",
        lunar_month_purnimanta="Chaitra",
        weekday="Wednesday",
    )
    names = {item["name"] for item in festivals}
    assert "Ugadi / Gudi Padwa" in names
    assert "Chaitra Navaratri Begins" in names


def test_varalakshmi_friday_before_purnima_in_shravana():
    festivals = detect_day_festivals(
        tithi_data={"name": "Dwadashi", "paksha": "Shukla", "number": 12},
        nakshatra={"name": "Hasta"},
        lunar_month="Shravana",
        weekday="Friday",
    )
    assert any(item["name"] == "Varalakshmi Vrata" for item in festivals)

    not_friday = detect_day_festivals(
        tithi_data={"name": "Dwadashi", "paksha": "Shukla", "number": 12},
        nakshatra={"name": "Hasta"},
        lunar_month="Shravana",
        weekday="Thursday",
    )
    assert all(item["name"] != "Varalakshmi Vrata" for item in not_friday)


def test_adhika_jyeshtha_month_naming_preserved_2026_05_24():
    panchang = PanchangService().calculate_panchang(
        datetime(2026, 5, 24, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )
    assert panchang["date"]["hindu"]["month"] == "Adhika Jyeshtha"
    assert panchang["date"]["hindu"]["is_adhika_masa"] is True
