"""
Upcoming civil dates for a given Nakshatra (birth-star lookup).

The Moon returns to the same Nakshatra roughly every 27.3 days. Each return
is located by its exact start/end crossing, then mapped to a civil date with
the same convention as the date -> star lookup (``panchang_datetime_for_date``):
the star prevailing at local noon (IST) owns the date. A short star that
misses every noon is assigned to the date of its midpoint, so no month is
ever skipped.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Dict, List

import swisseph as swe

from .astro_utils import (
    find_absolute_transition,
    get_julian_day,
    get_sidereal_position,
    ist_now,
    jd_to_datetime,
)
from .constants import NAKSHATRAS

_SPAN = 360.0 / 27.0
_MOON_MAX_SPEED = 15.5  # deg/day, upper bound used to seed without overshooting

_EXTRA_ALIASES = {
    "aswini": "Ashwini",
    "ashvini": "Ashwini",
    "kritika": "Krittika",
    "karthika": "Krittika",
    "mrigashirsha": "Mrigashira",
    "mrigasira": "Mrigashira",
    "arudra": "Ardra",
    "aridra": "Ardra",
    "punarvasu": "Punarvasu",
    "pushyami": "Pushya",
    "aslesha": "Ashlesha",
    "makha": "Magha",
    "pubba": "Purva Phalguni",
    "uttara": "Uttara Phalguni",
    "chitta": "Chitra",
    "swathi": "Swati",
    "visakha": "Vishakha",
    "jyestha": "Jyeshtha",
    "moola": "Mula",
    "purvashada": "Purva Ashadha",
    "uttarashada": "Uttara Ashadha",
    "sravana": "Shravana",
    "dhanishtha": "Dhanishta",
    "shatabhishak": "Shatabhisha",
    "satabhisha": "Shatabhisha",
    "purvabhadra": "Purva Bhadrapada",
    "uttarabhadra": "Uttara Bhadrapada",
    "revathi": "Revati",
}


def _key(name: str) -> str:
    return re.sub(r"[^a-z]", "", str(name or "").lower())


_INDEX_BY_KEY = {_key(n): i for i, n in enumerate(NAKSHATRAS)}
for _alias, _canonical in _EXTRA_ALIASES.items():
    _INDEX_BY_KEY.setdefault(_alias, NAKSHATRAS.index(_canonical))


def resolve_nakshatra_index(name: str) -> int:
    """Return the 0-based Nakshatra index, or raise ValueError if unknown."""
    idx = _INDEX_BY_KEY.get(_key(name))
    if idx is None:
        raise ValueError(f"Unknown nakshatra: {name!r}")
    return idx


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _display(dt: datetime) -> str:
    return dt.strftime("%d %b %Y, %I:%M %p")


def next_nakshatra_dates(name: str, limit: int = 8, now: datetime | None = None) -> List[Dict]:
    """Next ``limit`` civil dates (IST) on which ``name`` is the day's star."""
    idx = resolve_nakshatra_index(name)
    now = now or ist_now()
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    today: date = now.date()

    start_deg = idx * _SPAN
    end_deg = ((idx + 1) * _SPAN) % 360.0

    now_jd = get_julian_day(now)
    moon = get_sidereal_position(now_jd, swe.MOON)
    if int(moon / _SPAN) % 27 == idx:
        # Star is running now: its start lies behind us.
        jd_start = find_absolute_transition(now_jd, swe.MOON, start_deg)
    else:
        gap = (start_deg - moon) % 360.0
        seed = now_jd + max(0.0, gap - 10.0) / _MOON_MAX_SPEED
        jd_start = find_absolute_transition(seed, swe.MOON, start_deg)

    out: List[Dict] = []
    for _ in range(limit + 3):
        jd_end = find_absolute_transition(jd_start + 0.5, swe.MOON, end_deg)
        start_dt = jd_to_datetime(jd_start)
        end_dt = jd_to_datetime(jd_end)

        # Civil dates whose local noon falls inside the star's window.
        days: List[date] = []
        d = start_dt.date()
        while d <= end_dt.date():
            noon = datetime(d.year, d.month, d.day, 12, 0, 0)
            if start_dt <= noon < end_dt:
                days.append(d)
            d += timedelta(days=1)
        if not days:
            days = [(start_dt + (end_dt - start_dt) / 2).date()]

        for d in days:
            if d < today or len(out) >= limit:
                continue
            out.append(
                {
                    "event_date": d.isoformat(),
                    "weekday": d.strftime("%A"),
                    "days_away": (d - today).days,
                    "is_today": d == today,
                    "starts_at": _fmt(start_dt),
                    "ends_at": _fmt(end_dt),
                    "starts_at_display": _display(start_dt),
                    "ends_at_display": _display(end_dt),
                }
            )
        if len(out) >= limit:
            break
        # Sidereal month is ~27.32 days; seed just short of the next return.
        jd_start = find_absolute_transition(jd_start + 26.5, swe.MOON, start_deg)

    return out
