"""Festivals belong to the civil day, not to the instant the Panchang is opened."""
from datetime import date, datetime

from app.services.panchang import PanchangService
from app.services.panchang.festivals import detect_festivals_for_civil_day

BLR = (12.9716, 77.5946)


def _names(day: date) -> list[str]:
    return [item["name"] for item in detect_festivals_for_civil_day(day, *BLR)]


def test_bali_padyami_stays_listed_after_pratipada_ends():
    """10 Nov 2026: Pratipada ends ~2 PM, but the day is still Bali Padyami."""
    service = PanchangService()
    for hour in (0, 7, 13, 15, 20, 23):
        data = service.calculate_panchang(datetime(2026, 11, 10, hour, 30), *BLR, "Bengaluru")
        names = [item["name"] for item in data["festivals"]]
        assert names == ["Bali Padyami"], (hour, names)
        labels = [row["english"] for row in data["south_india_special"] if row["type"] == "festival"]
        assert labels == ["Bali Padyami (Bali Pratipada)"]


def test_deepavali_week_2026_matches_published_calendar():
    assert _names(date(2026, 11, 6)) == ["Dhanteras", "Pradosha Vrat"]
    assert _names(date(2026, 11, 8)) == ["Naraka Chaturdashi", "Deepavali (Lakshmi Puja)"]
    assert _names(date(2026, 11, 9)) == ["Amavasya"]
    assert _names(date(2026, 11, 10)) == ["Bali Padyami"]
    assert _names(date(2026, 11, 11)) == ["Bhai Dooj"]


def test_kala_based_festivals_2026():
    # Ashtami misses midnight on both nights; it is observed on 4 Sep.
    assert "Krishna Janmashtami" in _names(date(2026, 9, 4))
    assert "Krishna Janmashtami" not in _names(date(2026, 9, 3))
    # Dashami begins after sunrise on 20 Oct but covers aparahna that day.
    assert "Vijayadashami (Dussehra)" in _names(date(2026, 10, 20))
    assert "Vijayadashami (Dussehra)" not in _names(date(2026, 10, 21))
    assert "Ganesh Chaturthi" in _names(date(2026, 9, 14))
    assert "Maha Shivaratri" in _names(date(2026, 2, 15))


def test_month_festivals_not_repeated_in_adhika_masa():
    # 2026 has an Adhika Jyeshtha; Ganga Dussehra falls in the Nija month only.
    assert "Ganga Dussehra" not in _names(date(2026, 5, 25))
    assert "Ganga Dussehra" in _names(date(2026, 6, 24))


def test_tithi_end_time_is_stable_through_the_tithi():
    """End time used to drift (~12h after the query) early in a long tithi."""
    service = PanchangService()
    ends = {
        service.get_tithi(service.get_julian_day(datetime(2026, 11, 10, hour, 30)))["end_time"][:16]
        for hour in (15, 18, 21, 23)
    }
    assert ends == {"2026-11-11 15:53"}
