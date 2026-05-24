"""
Calendrical calculations: Ayana, Ruthu, Samvatsara, Hindu Calendar Info
"""

import swisseph as swe
from datetime import datetime
from typing import Dict
from .astro_utils import get_sidereal_position
from .constants import RASHIS, RUTHUS, SAMVATSARAS

LUNAR_MONTHS = [
    "Chaitra",
    "Vaishakha",
    "Jyeshtha",
    "Ashadha",
    "Shravana",
    "Bhadrapada",
    "Ashvina",
    "Kartika",
    "Margashirsha",
    "Pausha",
    "Magha",
    "Phalguni",
]

def get_moon_sign_data(jd: float) -> Dict:
    """Calculate Moon's Rashi"""
    moon_long = get_sidereal_position(jd, swe.MOON)
    rashi_num = int(moon_long / 30)

    return {
        "number": rashi_num + 1,
        "name": RASHIS[rashi_num],
        "moon_longitude": round(moon_long, 2),
    }

def get_ayana_data(jd: float) -> str:
    """Calculate Ayana"""
    sun_long = get_sidereal_position(jd, swe.SUN)
    if 270 <= sun_long or sun_long < 90:
        return "Uttarayana"
    else:
        return "Dakshinayana"

def get_ruthu_data(jd: float) -> str:
    """Calculate Ruthu"""
    sun_long = get_sidereal_position(jd, swe.SUN)
    if 330 <= sun_long or sun_long < 30:
        return "Vasanta"
    elif 30 <= sun_long < 90:
        return "Grishma"
    elif 90 <= sun_long < 150:
        return "Varsha"
    elif 150 <= sun_long < 210:
        return "Sharad"
    elif 210 <= sun_long < 270:
        return "Hemanta"
    else:
        return "Shishira"

def _phase_angle(jd: float) -> float:
    moon_long = get_sidereal_position(jd, swe.MOON)
    sun_long = get_sidereal_position(jd, swe.SUN)
    return (moon_long - sun_long) % 360

def _find_new_moon(jd: float, forward: bool) -> float:
    """Find previous/next conjunction by detecting the Moon-Sun phase wrap."""
    step = 0.25 if forward else -0.25
    prev_jd = jd
    prev_phase = _phase_angle(prev_jd)

    for _ in range(200):
        curr_jd = prev_jd + step
        curr_phase = _phase_angle(curr_jd)
        wrapped = (forward and curr_phase < prev_phase) or ((not forward) and curr_phase > prev_phase)
        if wrapped:
            lo, hi = (prev_jd, curr_jd) if prev_jd < curr_jd else (curr_jd, prev_jd)
            for _ in range(80):
                mid = (lo + hi) / 2.0
                mid_phase = _phase_angle(mid)
                if mid_phase > 180:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2.0
        prev_jd, prev_phase = curr_jd, curr_phase

    return jd

def _has_sankranti_between(start_jd: float, end_jd: float) -> bool:
    start_sign = int(get_sidereal_position(start_jd, swe.SUN) / 30)
    end_sign = int(get_sidereal_position(end_jd, swe.SUN) / 30)
    return start_sign != end_sign

def _get_lunar_month(dt: datetime, jd: float) -> Dict:
    """Return amanta/purnimanta lunar month with adhika detection."""
    del dt
    previous_new_moon = _find_new_moon(jd, forward=False)
    next_new_moon = _find_new_moon(jd, forward=True)
    next_solar_sign = int(get_sidereal_position(next_new_moon, swe.SUN) / 30)
    month_name = LUNAR_MONTHS[(next_solar_sign + 1) % 12]
    is_adhika = not _has_sankranti_between(previous_new_moon, next_new_moon)
    display_name = f"Adhika {month_name}" if is_adhika else month_name

    phase = _phase_angle(jd)
    paksha = "Shukla" if phase < 180 else "Krishna"
    purnimanta_name = display_name
    if paksha == "Krishna":
        purnimanta_name = LUNAR_MONTHS[next_solar_sign % 12]

    return {
        "amanta": display_name,
        "purnimanta": purnimanta_name,
        "display": display_name,
        "is_adhika": is_adhika,
    }

def get_samvatsara_data(year: int) -> Dict:
    """Calculate Samvatsara name"""
    shaka_year = year - 78
    samvatsara_index = (shaka_year + 11) % 60

    return {
        "number": samvatsara_index + 1,
        "name": SAMVATSARAS[samvatsara_index],
        "shaka_year": shaka_year,
        "kali_year": year + 3102,
        "cycle_year": samvatsara_index + 1,
    }

def get_hindu_calendar_info_data(dt: datetime, jd: float) -> Dict:
    """Calculate dynamic Hindu calendar information with proper Samvatsara alignment"""
    # Shaka year calculation: Year 0 of Shaka era was 78 CE
    # Shaka year changes on Chaitra Shukla Prathama (around March 21-April 14 CE)
    shaka_year = dt.year - 78
    if dt.month < 3 or (dt.month == 3 and dt.day < 21):
        shaka_year -= 1

    # Vikram Samvat = Shaka year + 135
    vikram_samvat = shaka_year + 135

    # Samvatsara (60-year cycle) calculation
    # Base calibration: Shaka 1909 (1987 CE) = Prabhava (index 0)
    # This is the standard Drik Panchang alignment
    base_shaka_year = 1909
    base_samvatsara_index = 0

    # Calculate Shaka Samvatsara index
    shaka_idx = (shaka_year - base_shaka_year + base_samvatsara_index) % 60
    shaka_name = SAMVATSARAS[shaka_idx]

    # Vikram Samvatsara has a separate traditional alignment from Shaka.
    # For 2026-05-24: Shaka 1948 is Parabhava, while Vikram 2083 is Siddharthi.
    vikram_idx = (shaka_idx + 13) % 60
    vikram_name = SAMVATSARAS[vikram_idx]

    # Solar position (for solar month/ritu)
    sun_long = get_sidereal_position(jd, swe.SUN)
    solar_month_idx = int(sun_long / 30)
    solar_month = RASHIS[solar_month_idx]

    diff = _phase_angle(jd)
    lunar_month = _get_lunar_month(dt, jd)

    paksha = "Shukla" if diff < 180 else "Krishna"
    ritu = get_ruthu_data(jd)

    return {
        "vikram_samvat": f"{vikram_samvat} {vikram_name}",
        "shaka_samvat": f"{shaka_year} {shaka_name}",
        "shaka_year": shaka_year,
        "samvatsara_name": shaka_name,
        "samvatsara_cycle_year": shaka_idx + 1,
        "vikram_samvatsara_name": vikram_name,
        "vikram_samvatsara_cycle_year": vikram_idx + 1,
        "solar_month": solar_month,
        "lunar_month_purnimanta": lunar_month["purnimanta"],
        "lunar_month_amanta": lunar_month["amanta"],
        "lunar_month": lunar_month["display"],
        "is_adhika_masa": lunar_month["is_adhika"],
        "paksha": paksha,
        "ritu": ritu,
    }
