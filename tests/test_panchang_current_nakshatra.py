from datetime import date, datetime, timezone

from app.services.panchang import PanchangService
from app.services.panchang.astro_utils import IST_ZONE, ist_now, panchang_datetime_for_date

BENGALURU = (12.9716, 77.5946, "Bengaluru")


def test_ist_now_is_naive_asia_kolkata_wall_clock():
    utc = datetime.now(timezone.utc)
    expected = utc.astimezone(IST_ZONE).replace(tzinfo=None)
    actual = ist_now()
    assert actual.tzinfo is None
    assert abs((actual - expected).total_seconds()) < 2


def test_panchang_datetime_uses_current_ist_for_today():
    now = datetime(2026, 8, 14, 10, 15, 0)
    assert panchang_datetime_for_date(date(2026, 8, 14), now=now) == now
    assert panchang_datetime_for_date("2026-08-14", now=now) == now
    assert panchang_datetime_for_date(date(2026, 8, 13), now=now) == datetime(2026, 8, 13, 12, 0, 0)


def test_bengaluru_nakshatra_updates_after_morning_transition():
    """Magha ended ~04:38 IST on 2026-08-14; 10:00 must show Purva Phalguni."""
    service = PanchangService()
    lat, lon, city = BENGALURU

    midnight = service.calculate_panchang(datetime(2026, 8, 14, 0, 0, 0), lat, lon, city)
    ten_am = service.calculate_panchang(datetime(2026, 8, 14, 10, 0, 0), lat, lon, city)

    midnight_nak = midnight["panchang"]["nakshatra"]
    ten_am_nak = ten_am["panchang"]["nakshatra"]

    assert midnight_nak["name"] == "Magha"
    assert midnight_nak["next_nakshatra"] == "Purva Phalguni"
    assert midnight_nak["end_time"].startswith("2026-08-14 04:38")

    assert ten_am_nak["name"] == "Purva Phalguni"
    assert ten_am["calculation_metadata"]["as_of_ist"] == "2026-08-14 10:00:00"
