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
    """Find the JD at which a cyclic (0-360) quantity reaches ``target_val``.

    Brackets the crossing by stepping from ``jd_start`` and then bisects. The
    earlier damped-step search could travel at most ~12 hours, so a limb ending
    later than that (most tithis right after they begin) got a bogus end time.
    """

    def signed_gap(jd: float) -> float:
        gap = (target_val - get_current_val_func(jd) + 360.0) % 360.0
        return gap - 360.0 if gap > 180.0 else gap

    prev_jd = jd_start
    prev_gap = signed_gap(prev_jd)
    if abs(prev_gap) < 1e-7:
        return jd_start

    step = 0.02 if prev_gap > 0 else -0.02  # ~29 minutes
    for _ in range(3000):  # ~60 days
        curr_jd = prev_jd + step
        curr_gap = signed_gap(curr_jd)
        crossed = (prev_gap > 0) != (curr_gap > 0) and abs(curr_gap - prev_gap) < 180.0
        if crossed:
            lo, hi = prev_jd, curr_jd
            lo_gap = prev_gap
            for _ in range(50):
                mid = (lo + hi) / 2.0
                mid_gap = signed_gap(mid)
                if (mid_gap > 0) == (lo_gap > 0):
                    lo, lo_gap = mid, mid_gap
                else:
                    hi = mid
            return (lo + hi) / 2.0
        prev_jd, prev_gap = curr_jd, curr_gap

    return jd_start

def find_absolute_transition(jd_start: float, body_id: int, target_deg: float) -> float:
    """Find when a planet reaches a specific absolute longitude"""
    def get_pos(jd):
        return get_sidereal_position(jd, body_id)
    return find_transition(jd_start, target_deg, get_pos)
