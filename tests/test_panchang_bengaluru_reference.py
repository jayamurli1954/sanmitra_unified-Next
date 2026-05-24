from datetime import datetime

from app.services.panchang import PanchangService


def test_bengaluru_panchang_reference_2026_05_24():
    panchang = PanchangService().calculate_panchang(
        datetime(2026, 5, 24, 12, 0, 0),
        12.9716,
        77.5946,
        "Bengaluru",
    )

    assert panchang["date"]["hindu"]["month"] == "Adhika Jyeshtha"
    assert panchang["date"]["hindu"]["is_adhika_masa"] is True
    assert panchang["date"]["hindu"]["ritu"] == "Grishma"

    assert panchang["sun_moon"]["moonrise"] == "1:06 PM"
    assert panchang["sun_moon"]["moonset"] == "12:54 AM"

    assert panchang["panchang"]["tithi"]["full_name"] == "Shukla Navami"
    assert panchang["panchang"]["nakshatra"]["name"] == "Purva Phalguni"
    assert panchang["panchang"]["yoga"]["name"] == "Harshana"

    varjyam = panchang["additional_inauspicious_times"]["varjyam"]
    assert len(varjyam) == 1
    assert varjyam[0]["start"] == "10:23:00"
    assert varjyam[0]["end"] == "12:02:00"
    assert 98 <= varjyam[0]["duration_minutes"] <= 100
