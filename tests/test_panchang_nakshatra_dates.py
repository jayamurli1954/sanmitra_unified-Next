from datetime import date, datetime

import pytest

from app.services.panchang import PanchangService
from app.services.panchang.constants import NAKSHATRAS
from app.services.panchang.nakshatra_dates import next_nakshatra_dates, resolve_nakshatra_index

NOW = datetime(2026, 11, 16, 12, 56, 0)


def _star_at_noon(d: date) -> str:
    service = PanchangService()
    jd = service.get_julian_day(datetime(d.year, d.month, d.day, 12, 0, 0))
    return service.get_nakshatra(jd)["name"]


def test_resolve_nakshatra_index_accepts_spelling_variants():
    assert resolve_nakshatra_index("Ashwini") == 0
    assert resolve_nakshatra_index("purva phalguni") == 10
    assert resolve_nakshatra_index("Moola") == NAKSHATRAS.index("Mula")
    with pytest.raises(ValueError):
        resolve_nakshatra_index("NotAStar")


@pytest.mark.parametrize("star", ["Ashwini", "Rohini", "Mula", "Revati"])
def test_next_dates_are_distinct_future_and_roughly_monthly(star):
    rows = next_nakshatra_dates(star, limit=8, now=NOW)
    assert len(rows) == 8
    dates = [date.fromisoformat(r["event_date"]) for r in rows]
    assert dates == sorted(set(dates)), "dates must be distinct and ascending"
    assert all(d >= NOW.date() for d in dates)
    # Eight rows span six to seven sidereal months (a long star that covers
    # two noons contributes two consecutive dates).
    assert 150 <= (dates[-1] - dates[0]).days <= 200
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    assert all(g == 1 or 26 <= g <= 29 for g in gaps)
    for r, d in zip(rows, dates):
        assert r["days_away"] == (d - NOW.date()).days
        assert r["is_today"] == (d == NOW.date())
        assert r["weekday"] == d.strftime("%A")
        assert r["starts_at"] < r["ends_at"]


def test_dates_agree_with_date_to_star_lookup():
    """Every returned date must show the same star in the noon-based lookup."""
    for star in ("Ashwini", "Pushya", "Shravana"):
        for row in next_nakshatra_dates(star, limit=6, now=NOW):
            d = date.fromisoformat(row["event_date"])
            start = datetime.strptime(row["starts_at"], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(row["ends_at"], "%Y-%m-%d %H:%M:%S")
            noon = datetime(d.year, d.month, d.day, 12, 0, 0)
            if start <= noon < end:
                assert _star_at_noon(d) == star
            else:  # short star that misses every noon: midpoint date
                assert start.date() <= d <= end.date()


def test_every_star_is_found_within_one_lunar_cycle():
    for star in NAKSHATRAS:
        first = next_nakshatra_dates(star, limit=1, now=NOW)[0]
        assert 0 <= first["days_away"] <= 28
