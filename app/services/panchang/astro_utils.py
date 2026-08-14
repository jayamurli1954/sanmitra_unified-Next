"""
Astronomical utility functions for Panchang calculations
"""

from __future__ import annotations

import swisseph as swe
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

IST_ZONE = ZoneInfo("Asia/Kolkata")


def ist_now() -> datetime:
    """Naive Asia/Kolkata wall-clock time.

    ``get_julian_day`` treats naive datetimes as IST. Production hosts often
    run in UTC, so ``datetime.now()`` would evaluate the Moon several hours
    early and leave overnight nakshatra/tithi transitions stuck on the previous
    limb until late morning.
    """
    return datetime.now(IST_ZONE).replace(tzinfo=None)


def panchang_datetime_for_date(target_date: date | datetime | str, now: datetime | None = None) -> datetime:
    """Choose the instant used to evaluate tithi/nakshatra for a civil date.

    Today uses the current IST clock so Five Limbs follow live transitions.
    Other dates use local noon so a midnight snapshot cannot hide a pre-dawn
    nakshatra change that applies for most of the waking day.
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()

    current = now or ist_now()
    if current.tzinfo is not None:
        current = current.replace(tzinfo=None)
    if target_date == current.date():
        return current
    return datetime(target_date.year, target_date.month, target_date.day, 12, 0, 0)


def get_julian_day(dt: datetime) -> float:
    """Convert datetime (Assumed IST) to Julian Day (UT)"""
    dec_hour_ist = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    dec_hour_ut = dec_hour_ist - 5.5
    return swe.julday(dt.year, dt.month, dt.day, dec_hour_ut)

def get_sidereal_position(jd: float, planet: int):
    """Get TRUE sidereal (Nirayana) longitude using Lahiri"""
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    result = swe.calc_ut(jd, planet, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    return result[0][0] % 360

def jd_to_datetime(jd: float) -> datetime:
    """Convert Julian day to datetime (IST)"""
    result = swe.revjul(jd)
    year, month, day, hour = result
    hours = int(hour)
    minutes = int((hour - hours) * 60)
    seconds = int(((hour - hours) * 60 - minutes) * 60)
    dt_ut = datetime(year, month, day, hours, minutes, seconds)
    return dt_ut + timedelta(hours=5, minutes=30)

def find_transition(jd_start: float, target_val: float, get_current_val_func) -> float:
    """Generic binary search for transition time"""
    jd = jd_start
    step = 0.01  # ~15 minutes
    for _ in range(200):
        current = get_current_val_func(jd)
        
        # Normalize diff to [-180, 180]
        diff = (target_val - current + 360) % 360
        if diff > 180: diff -= 360

        if abs(diff) < 0.0001:
            return jd

        if diff > 0:
            jd += step
        else:
            jd -= step

        # Reduce step size
        step *= 0.5 if abs(diff) < 0.1 else 0.98

    return jd

def find_absolute_transition(jd_start: float, body_id: int, target_deg: float) -> float:
    """Find when a planet reaches a specific absolute longitude"""
    def get_pos(jd):
        return get_sidereal_position(jd, body_id)
    return find_transition(jd_start, target_deg, get_pos)
