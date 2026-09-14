"""
Major Hindu festival detection for MandirMitra Panchang.

Rule shape (Amanta-first; expandable, non-exhaustive)::

    {"name": "...", "masa": "Bhadrapada", "paksha": "Shukla", "tithi": "Chaturthi"}
    {"name": "...", "masa": "Shravana", "masa_purnimanta": "Bhadrapada",
     "paksha": "Krishna", "tithi": "Ashtami", "nakshatra": "Rohini"}

Current state:
- Matches curated pan-India festivals via masa + paksha + tithi (+ nakshatra /
  weekday / solar where needed).
- Krishna-paksha month names often differ Amanta vs Purnimanta; rules store
  Amanta ``masa`` and optional ``masa_purnimanta`` and match either.

Gap / deferred:
- Not a complete Hindu calendar. Temple-local calendars, some regional Jayantis,
  and muhurta-precise midnight crossings remain out of scope for v1.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import swisseph as swe

from .astro_utils import get_sidereal_position
from .constants import TITHIS

# Canonical Amanta month -> accepted aliases.
MONTH_ALIASES: Dict[str, Set[str]] = {
    "Chaitra": {"Chaitra"},
    "Vaishakha": {"Vaishakha", "Vaisakha"},
    "Jyeshtha": {"Jyeshtha", "Jyeshta"},
    "Ashadha": {"Ashadha", "Aashadha"},
    "Shravana": {"Shravana", "Sravana"},
    "Bhadrapada": {"Bhadrapada", "Bhadra", "Bhadrapad"},
    "Ashvina": {"Ashvina", "Ashwin", "Ashwayuja", "Ashwayuj", "Asvayuja"},
    "Kartika": {"Kartika", "Kartik", "Karthika"},
    "Margashirsha": {"Margashirsha", "Margashira", "Margasira"},
    "Pausha": {"Pausha", "Pausa", "Pushya"},
    "Magha": {"Magha"},
    "Phalguni": {"Phalguni", "Phalguna", "Phalgun"},
}

NAKSHATRA_ALIASES: Dict[str, Set[str]] = {
    "Ashwini": {"Ashwini", "Aswini"},
    "Bharani": {"Bharani"},
    "Krittika": {"Krittika", "Krithika"},
    "Rohini": {"Rohini"},
    "Mrigashira": {"Mrigashira", "Mrigashirsha"},
    "Ardra": {"Ardra"},
    "Punarvasu": {"Punarvasu"},
    "Pushya": {"Pushya", "Pushya"},
    "Ashlesha": {"Ashlesha", "Aslesha"},
    "Magha": {"Magha"},
    "Purva Phalguni": {"Purva Phalguni", "Poorva Phalguni"},
    "Uttara Phalguni": {"Uttara Phalguni"},
    "Hasta": {"Hasta"},
    "Chitra": {"Chitra", "Chithira"},
    "Swati": {"Swati"},
    "Vishakha": {"Vishakha", "Visakha"},
    "Anuradha": {"Anuradha"},
    "Jyeshtha": {"Jyeshtha", "Jyeshta"},
    "Moola": {"Moola", "Mula"},
    "Purva Ashadha": {"Purva Ashadha", "Purvashada", "Poorvashada"},
    "Uttara Ashadha": {"Uttara Ashadha", "Uttarashada"},
    "Shravana": {"Shravana", "Sravana", "Thiruvonam"},
    "Dhanishta": {"Dhanishta", "Dhanishtha"},
    "Shatabhisha": {"Shatabhisha", "Shatabhisha"},
    "Purva Bhadrapada": {"Purva Bhadrapada"},
    "Uttara Bhadrapada": {"Uttara Bhadrapada"},
    "Revati": {"Revati"},
}


def _f(
    name: str,
    *,
    masa: str | Sequence[str] | None = None,
    masa_purnimanta: str | Sequence[str] | None = None,
    paksha: str | None = None,
    tithi: str | None = None,
    nakshatra: str | Sequence[str] | None = None,
    nakshatra_mode: str = "preferred",  # preferred | required | ignore
    weekday: str | None = None,
    rule: str | None = None,  # special: varalakshmi | onam | makar_sankranti | mesha_sankranti
    importance: str = "major",
    ftype: str = "festival",
    description: str = "",
    observances: Sequence[str] | None = None,
    benefits: Sequence[str] | None = None,
    labels: Tuple[str, str, str] | None = None,
    suppress_generic: Sequence[str] | None = None,
) -> Dict:
    months = list(masa) if isinstance(masa, (list, tuple)) else ([masa] if masa else [])
    p_months = (
        list(masa_purnimanta)
        if isinstance(masa_purnimanta, (list, tuple))
        else ([masa_purnimanta] if masa_purnimanta else [])
    )
    naks = (
        list(nakshatra)
        if isinstance(nakshatra, (list, tuple))
        else ([nakshatra] if nakshatra else [])
    )
    return {
        "name": name,
        "type": ftype,
        "importance": importance,
        "months": months,
        "purnimanta_months": p_months,
        "paksha": paksha,
        "tithi": tithi,
        "nakshatras": naks,
        "nakshatra_mode": nakshatra_mode,
        "weekday": weekday,
        "rule": rule,
        "description": description or name,
        "observances": list(observances or ["Temple worship", "Charity", "Family observance"]),
        "benefits": list(benefits or ["Devotion", "Auspicious observance"]),
        "labels": labels or (name, name, name),
        "suppress_generic": list(suppress_generic or []),
    }


# Curated catalog — not exhaustive. Expand by appending rules.
MAJOR_FESTIVAL_CATALOG: List[Dict] = [
    # --- Chaitra ---
    _f(
        "Ugadi / Gudi Padwa",
        masa="Chaitra",
        paksha="Shukla",
        tithi="Pratipada",
        description="Chandramana Ugadi / Gudi Padwa - lunar new year (Chaitra Shukla Pratipada)",
        labels=("Ugadi / Gudi Padwa", "ಉಗಾದಿ / ಗುಡಿ ಪಡ್ವಾ", "युगादि / गुडी पडवा"),
    ),
    _f(
        "Chaitra Navaratri Begins",
        masa="Chaitra",
        paksha="Shukla",
        tithi="Pratipada",
        description="Chaitra / Vasanta Navaratri begins on Chaitra Shukla Pratipada",
        labels=("Chaitra Navaratri Begins", "ಚೈತ್ರ ನವರಾತ್ರಿ ಆರಂಭ", "चैत्र नवरात्रि आरम्भ"),
    ),
    _f(
        "Rama Navami",
        masa="Chaitra",
        paksha="Shukla",
        tithi="Navami",
        nakshatra="Punarvasu",
        nakshatra_mode="preferred",
        description="Rama Navami - Chaitra Shukla Navami (Punarvasu preferred)",
        labels=("Rama Navami", "ರಾಮ ನವಮಿ", "राम नवमी"),
    ),
    _f(
        "Hanuman Jayanti",
        masa="Chaitra",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra="Chitra",
        nakshatra_mode="preferred",
        description="Hanuman Jayanti - Chaitra Shukla Purnima (many traditions; Chitra preferred)",
        labels=("Hanuman Jayanti", "ಹನುಮಾನ್ ಜಯಂತಿ", "हनुमान् जयन्ती"),
        suppress_generic=["Purnima"],
    ),
    # --- Vaishakha ---
    _f(
        "Akshaya Tritiya",
        masa="Vaishakha",
        paksha="Shukla",
        tithi="Tritiya",
        nakshatra="Rohini",
        nakshatra_mode="preferred",
        description="Akshaya Tritiya - Vaishakha Shukla Tritiya (Rohini often auspicious)",
        labels=("Akshaya Tritiya", "ಅಕ್ಷಯ ತೃತೀಯ", "अक्षय तृतीया"),
    ),
    _f(
        "Narasimha Jayanti",
        masa="Vaishakha",
        paksha="Shukla",
        tithi="Chaturdashi",
        nakshatra="Swati",
        nakshatra_mode="preferred",
        description="Narasimha Jayanti - Vaishakha Shukla Chaturdashi (Swati preferred)",
        labels=("Narasimha Jayanti", "ನರಸಿಂಹ ಜಯಂತಿ", "नरसिंह जयन्ती"),
    ),
    _f(
        "Buddha Purnima",
        masa="Vaishakha",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra="Vishakha",
        nakshatra_mode="preferred",
        description="Buddha Purnima / Vesak - Vaishakha Shukla Purnima",
        labels=("Buddha Purnima", "ಬುದ್ಧ ಪೂರ್ಣಿಮಾ", "बुद्ध पूर्णिमा"),
        suppress_generic=["Purnima"],
    ),
    # --- Jyeshtha ---
    _f(
        "Vat Savitri Vrat",
        masa="Jyeshtha",
        paksha="Krishna",
        tithi="Amavasya",
        description="Vat Savitri Vrat - Jyeshtha Krishna Amavasya (Amanta)",
        labels=("Vat Savitri Vrat", "ವಟ ಸಾವಿತ್ರಿ ವ್ರತ", "वट सावित्री व्रत"),
        suppress_generic=["Amavasya"],
    ),
    _f(
        "Ganga Dussehra",
        masa="Jyeshtha",
        paksha="Shukla",
        tithi="Dashami",
        nakshatra="Hasta",
        nakshatra_mode="preferred",
        description="Ganga Dussehra - Jyeshtha Shukla Dashami",
        labels=("Ganga Dussehra", "ಗಂಗಾ ದಶಹರಾ", "गङ्गा दशहरा"),
    ),
    # --- Ashadha ---
    _f(
        "Jagannath Rath Yatra",
        masa="Ashadha",
        paksha="Shukla",
        tithi="Dwitiya",
        nakshatra="Pushya",
        nakshatra_mode="preferred",
        description="Jagannath Rath Yatra - Ashadha Shukla Dwitiya",
        labels=("Jagannath Rath Yatra", "ಜಗನ್ನಾಥ ರಥಯಾತ್ರೆ", "जगन्नाथ रथयात्रा"),
    ),
    _f(
        "Devshayani Ekadashi",
        masa="Ashadha",
        paksha="Shukla",
        tithi="Ekadashi",
        description="Devshayani / Sayana Ekadashi - Ashadha Shukla Ekadashi; Vishnu enters yoga-nidra",
        labels=("Devshayani Ekadashi", "ದೇವಶಯನಿ ಏಕಾದಶಿ", "देवशयनी एकादशी"),
        suppress_generic=["Ekadashi"],
    ),
    _f(
        "Guru Purnima",
        masa="Ashadha",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra=["Purva Ashadha", "Uttara Ashadha"],
        nakshatra_mode="preferred",
        description="Guru Purnima - Ashadha Shukla Purnima",
        labels=("Guru Purnima", "ಗುರು ಪೂರ್ಣಿಮಾ", "गुरु पूर्णिमा"),
        suppress_generic=["Purnima"],
    ),
    # --- Shravana ---
    _f(
        "Naga Panchami",
        masa="Shravana",
        paksha="Shukla",
        tithi="Panchami",
        nakshatra="Ashlesha",
        nakshatra_mode="preferred",
        description="Naga Panchami - Shravana Shukla Panchami (Ashlesha often significant)",
        labels=("Naga Panchami", "ನಾಗ ಪಂಚಮಿ", "नाग पञ्चमी"),
    ),
    _f(
        "Varalakshmi Vrata",
        masa="Shravana",
        paksha="Shukla",
        rule="varalakshmi",
        weekday="Friday",
        description="Varalakshmi Vrata - Friday before Shravana Shukla Purnima",
        labels=("Varalakshmi Vrata", "ವರಲಕ್ಷ್ಮಿ ವ್ರತ", "वरलक्ष्मी व्रत"),
    ),
    _f(
        "Raksha Bandhan",
        masa="Shravana",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra="Shravana",
        nakshatra_mode="preferred",
        description="Raksha Bandhan - Shravana Shukla Purnima",
        labels=("Raksha Bandhan", "ರಕ್ಷಾ ಬಂಧನ", "रक्षा बन्धन"),
        suppress_generic=["Purnima"],
    ),
    _f(
        "Upakarma",
        masa="Shravana",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra="Shravana",
        nakshatra_mode="preferred",
        description="Upakarma / Avani Avittam - Shravana Shukla Purnima (Shravana nakshatra)",
        labels=("Upakarma", "ಉಪಾಕರ್ಮ", "उपाकर्म"),
        suppress_generic=["Purnima"],
    ),
    # --- Bhadrapada (Amanta) / Janmashtami uses Shravana Amanta = Bhadrapada Purnimanta ---
    _f(
        "Krishna Janmashtami",
        masa="Shravana",
        masa_purnimanta="Bhadrapada",
        paksha="Krishna",
        tithi="Ashtami",
        nakshatra="Rohini",
        nakshatra_mode="preferred",
        description=(
            "Krishna Janmashtami - Krishna Ashtami with Rohini preferred "
            "(Amanta Shravana / Purnimanta Bhadrapada)"
        ),
        labels=("Krishna Janmashtami", "ಕೃಷ್ಣ ಜನ್ಮಾಷ್ಟಮಿ", "कृष्ण जन्माष्टमी"),
    ),
    _f(
        "Hartalika Teej",
        masa="Bhadrapada",
        paksha="Shukla",
        tithi="Tritiya",
        description="Hartalika Teej - Bhadrapada Shukla Tritiya",
        labels=("Hartalika Teej", "ಹರತಾಲಿಕಾ ತೀಜ್", "हरतालिका तीज"),
    ),
    _f(
        "Ganesh Chaturthi",
        masa="Bhadrapada",
        paksha="Shukla",
        tithi="Chaturthi",
        description="Ganesh / Vinayaka Chaturthi - Bhadrapada Shukla Chaturthi",
        observances=[
            "Install / worship Ganesha murti (Ganapati sthapana)",
            "Offer modaka, durva, and flowers",
            "Chant Ganapati Atharvashirsha / Ganesha mantras",
            "Temple visits, charity, and community celebrations",
        ],
        benefits=["Removes obstacles", "Wisdom and auspicious beginnings"],
        labels=(
            "Ganesh Chaturthi (Vinayaka Chaturthi)",
            "ಗಣೇಶ ಚತುರ್ಥಿ (ವಿನಾಯಕ ಚತುರ್ಥಿ)",
            "गणेश चतुर्थी (विनायक चतुर्थी)",
        ),
    ),
    _f(
        "Rishi Panchami",
        masa="Bhadrapada",
        paksha="Shukla",
        tithi="Panchami",
        description="Rishi Panchami - Bhadrapada Shukla Panchami",
        labels=("Rishi Panchami", "ಋಷಿ ಪಂಚಮಿ", "ऋषि पञ्चमी"),
    ),
    _f(
        "Ananta Chaturdashi",
        masa="Bhadrapada",
        paksha="Shukla",
        tithi="Chaturdashi",
        description="Ananta Chaturdashi - Bhadrapada Shukla Chaturdashi (often Ganesh visarjan day)",
        labels=("Ananta Chaturdashi", "ಅನಂತ ಚತುರ್ದಶಿ", "अनन्त चतुर्दशी"),
    ),
    # --- Ashvina ---
    _f(
        "Sharada Navaratri Begins",
        masa="Ashvina",
        paksha="Shukla",
        tithi="Pratipada",
        description="Sharada Navaratri / Ghatasthapana - Ashvina Shukla Pratipada",
        labels=(
            "Sharada Navaratri Begins (Ghatasthapana)",
            "ಶಾರದಾ ನವರಾತ್ರಿ ಆರಂಭ (ಘಟಸ್ಥಾಪನ)",
            "शारदा नवरात्रि आरम्भ (घटस्थापन)",
        ),
    ),
    _f(
        "Durga Ashtami",
        masa="Ashvina",
        paksha="Shukla",
        tithi="Ashtami",
        description="Durga Ashtami / Maha Ashtami - Ashvina Shukla Ashtami",
        labels=("Durga Ashtami", "ದುರ್ಗಾ ಅಷ್ಟಮಿ", "दुर्गा अष्टमी"),
    ),
    _f(
        "Maha Navami",
        masa="Ashvina",
        paksha="Shukla",
        tithi="Navami",
        description="Maha Navami - Ashvina Shukla Navami",
        labels=("Maha Navami", "ಮಹಾ ನವಮಿ", "महा नवमी"),
    ),
    _f(
        "Vijayadashami (Dussehra)",
        masa="Ashvina",
        paksha="Shukla",
        tithi="Dashami",
        description="Vijayadashami / Dussehra - Ashvina Shukla Dashami",
        labels=("Vijayadashami (Dussehra)", "ವಿಜಯದಶಮಿ (ದಸರಾ)", "विजयदशमी (दशहरा)"),
    ),
    _f(
        "Kojagari Purnima",
        masa="Ashvina",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra="Ashwini",
        nakshatra_mode="preferred",
        description="Kojagari / Sharad Purnima - Ashvina Shukla Purnima",
        labels=("Kojagari Purnima", "ಕೋಜಾಗರಿ ಪೂರ್ಣಿಮಾ", "कोजागरी पूर्णिमा"),
        suppress_generic=["Purnima"],
    ),
    # --- Kartika (Deepavali cluster: Amanta Ashvina Krishna = Purnimanta Kartika) ---
    _f(
        "Karwa Chauth",
        masa="Ashvina",
        masa_purnimanta="Kartika",
        paksha="Krishna",
        tithi="Chaturthi",
        description="Karwa Chauth - Krishna Chaturthi (Amanta Ashvina / Purnimanta Kartika)",
        labels=("Karwa Chauth", "ಕರ್ವಾ ಚೌತ್", "करवा चौथ"),
    ),
    _f(
        "Dhanteras",
        masa="Ashvina",
        masa_purnimanta="Kartika",
        paksha="Krishna",
        tithi="Trayodashi",
        description="Dhanteras - Krishna Trayodashi before Deepavali",
        labels=("Dhanteras", "ಧನತ್ರಯೋದಶಿ", "धनत्रयोदशी"),
    ),
    _f(
        "Naraka Chaturdashi",
        masa="Ashvina",
        masa_purnimanta="Kartika",
        paksha="Krishna",
        tithi="Chaturdashi",
        description="Naraka Chaturdashi / Choti Diwali - Krishna Chaturdashi",
        labels=("Naraka Chaturdashi", "ನರಕ ಚತುರ್ದಶಿ", "नरक चतुर्दशी"),
    ),
    _f(
        "Deepavali (Lakshmi Puja)",
        masa="Ashvina",
        masa_purnimanta="Kartika",
        paksha="Krishna",
        tithi="Amavasya",
        description="Deepavali / Diwali Lakshmi Puja - Krishna Amavasya",
        labels=("Deepavali (Lakshmi Puja)", "ದೀಪಾವಳಿ (ಲಕ್ಷ್ಮಿ ಪೂಜೆ)", "दीपावली (लक्ष्मी पूजा)"),
        suppress_generic=["Amavasya"],
    ),
    _f(
        "Bali Padyami",
        masa="Kartika",
        paksha="Shukla",
        tithi="Pratipada",
        description="Bali Padyami / Govardhan - Kartika Shukla Pratipada",
        labels=("Bali Padyami", "ಬಲಿ ಪಾಡ್ಯಮಿ", "बलि पाद्यमी"),
    ),
    _f(
        "Bhai Dooj",
        masa="Kartika",
        paksha="Shukla",
        tithi="Dwitiya",
        description="Bhai Dooj / Yama Dwitiya - Kartika Shukla Dwitiya",
        labels=("Bhai Dooj", "ಭಾಯಿ ದೂಜ್", "भाई दूज"),
    ),
    _f(
        "Tulasi Vivaha",
        masa="Kartika",
        paksha="Shukla",
        tithi="Dwadashi",
        description="Tulasi Vivaha - Kartika Shukla Dwadashi (common South tradition)",
        labels=("Tulasi Vivaha", "ತುಳಸಿ ವಿವಾಹ", "तुलसी विवाह"),
    ),
    _f(
        "Kartika Purnima",
        masa="Kartika",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra="Krittika",
        nakshatra_mode="preferred",
        description="Kartika Purnima / Kartika Deepotsava - Kartika Shukla Purnima",
        labels=("Kartika Purnima", "ಕಾರ್ತಿಕ ಪೂರ್ಣಿಮಾ", "कार्तिक पूर्णिमा"),
        suppress_generic=["Purnima"],
    ),
    # --- Margashirsha ---
    _f(
        "Gita Jayanti",
        masa="Margashirsha",
        paksha="Shukla",
        tithi="Ekadashi",
        description="Gita Jayanti - Margashirsha Shukla Ekadashi",
        labels=("Gita Jayanti", "ಗೀತಾ ಜಯಂತಿ", "गीता जयन्ती"),
        suppress_generic=["Ekadashi"],
    ),
    _f(
        "Dattatreya Jayanti",
        masa="Margashirsha",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra="Mrigashira",
        nakshatra_mode="preferred",
        description="Dattatreya Jayanti - Margashirsha Shukla Purnima (Mrigashira preferred)",
        labels=("Dattatreya Jayanti", "ದತ್ತಾತ್ರೇಯ ಜಯಂತಿ", "दत्तात्रेय जयन्ती"),
        suppress_generic=["Purnima"],
    ),
    # --- Pausha ---
    _f(
        "Pausha Putrada Ekadashi",
        masa="Pausha",
        paksha="Shukla",
        tithi="Ekadashi",
        description="Pausha Putrada Ekadashi - Pausha Shukla Ekadashi",
        labels=("Pausha Putrada Ekadashi", "ಪುಷ್ಯ ಪುತ್ರದಾ ಏಕಾದಶಿ", "पौष पुत्रदा एकादशी"),
        suppress_generic=["Ekadashi"],
    ),
    # --- Magha ---
    _f(
        "Vasant Panchami",
        masa="Magha",
        paksha="Shukla",
        tithi="Panchami",
        description="Vasant Panchami / Saraswati Puja - Magha Shukla Panchami",
        labels=("Vasant Panchami", "ವಸಂತ ಪಂಚಮಿ", "वसन्त पञ्चमी"),
    ),
    _f(
        "Ratha Saptami",
        masa="Magha",
        paksha="Shukla",
        tithi="Saptami",
        description="Ratha Saptami - Magha Shukla Saptami; Surya worship",
        labels=("Ratha Saptami", "ರಥಸಪ್ತಮಿ", "रथसप्तमी"),
    ),
    _f(
        "Bhishma Ashtami",
        masa="Magha",
        paksha="Shukla",
        tithi="Ashtami",
        description="Bhishma Ashtami - Magha Shukla Ashtami",
        labels=("Bhishma Ashtami", "ಭೀಷ್ಮ ಅಷ್ಟಮಿ", "भीष्म अष्टमी"),
    ),
    _f(
        "Magha Purnima",
        masa="Magha",
        paksha="Shukla",
        tithi="Purnima",
        nakshatra="Magha",
        nakshatra_mode="preferred",
        description="Magha Purnima - Magha Shukla Purnima",
        labels=("Magha Purnima", "ಮಾಘ ಪೂರ್ಣಿಮಾ", "माघ पूर्णिमा"),
        suppress_generic=["Purnima"],
    ),
    # --- Phalguna / Magha for Shivaratri ---
    _f(
        "Maha Shivaratri",
        masa="Magha",
        masa_purnimanta=["Phalguni", "Phalguna"],
        paksha="Krishna",
        tithi="Chaturdashi",
        nakshatra=["Ardra", "Dhanishta", "Shatabhisha"],
        nakshatra_mode="preferred",
        description=(
            "Maha Shivaratri - Krishna Chaturdashi "
            "(Amanta Magha / Purnimanta Phalguna)"
        ),
        labels=("Maha Shivaratri", "ಮಹಾ ಶಿವರಾತ್ರಿ", "महा शिवरात्रि"),
    ),
    _f(
        "Holika Dahan",
        masa=["Phalguni", "Phalguna"],
        paksha="Shukla",
        tithi="Purnima",
        description="Holika Dahan - Phalguna Shukla Purnima evening (colour festival eve)",
        labels=("Holika Dahan", "ಹೋಲಿಕಾ ದಹನ", "होलिका दहन"),
        suppress_generic=["Purnima"],
    ),
    _f(
        "Holi",
        masa=["Phalguni", "Phalguna"],
        paksha="Shukla",
        tithi="Purnima",
        nakshatra=["Purva Phalguni", "Uttara Phalguni"],
        nakshatra_mode="preferred",
        description="Holi - Phalguna Shukla Purnima (Phalguni stars preferred)",
        labels=("Holi", "ಹೋಳಿ", "होली"),
        suppress_generic=["Purnima"],
    ),
    # --- Solar / regional specials (matched via rule) ---
    _f(
        "Makar Sankranti",
        rule="makar_sankranti",
        description="Makar Sankranti - Sun enters Makara; harvest / Uttarayana observance",
        labels=("Makar Sankranti", "ಮಕರ ಸಂಕ್ರಾಂತಿ", "मकर सङ्क्रान्ति"),
    ),
    _f(
        "Mesha Sankranti (Sauramana New Year)",
        rule="mesha_sankranti",
        description="Mesha Sankranti - Sauramana / solar new year (Sun enters Mesha)",
        labels=(
            "Mesha Sankranti (Sauramana New Year)",
            "ಮೇಷ ಸಂಕ್ರಾಂತಿ (ಸೌರಮಾನ ನವವರ್ಷ)",
            "मेष सङ्क्रान्ति (सौरमान नववर्ष)",
        ),
    ),
    _f(
        "Onam",
        rule="onam",
        nakshatra="Shravana",
        nakshatra_mode="required",
        description="Thiruvonam (Onam) - Shravana nakshatra in Malayalam Chingam month",
        labels=("Onam (Thiruvonam)", "ಓಣಂ (ತಿರುವೋಣಂ)", "ओणम् (तिरुवोणम्)"),
    ),
]

RECURRING_OBSERVANCES: List[Dict] = [
    _f(
        "Ekadashi",
        tithi="Ekadashi",
        ftype="fasting",
        description="Fasting day dedicated to Lord Vishnu",
        observances=[
            "Avoid grains, beans, onion and garlic",
            "Fruits, milk, sabudana allowed per custom",
        ],
        labels=("Ekadashi Fasting", "ಏಕಾದಶಿ ಉಪವಾಸ", "एकादशी व्रतम्"),
    ),
    _f(
        "Pradosha Vrat",
        tithi="Trayodashi",
        ftype="worship",
        importance="medium",
        description="Auspicious twilight worship of Lord Shiva",
        labels=("Pradosha Vrat", "ಪ್ರದೋಷ ವ್ರತ", "प्रदोष व्रतम्"),
    ),
    _f(
        "Sankashta Chaturthi",
        tithi="Chaturthi",
        paksha="Krishna",
        ftype="fasting",
        importance="medium",
        description="Monthly Krishna Chaturthi dedicated to Lord Ganesha",
        labels=("Sankashta Chaturthi", "ಸಂಕಷ್ಟ ಚತುರ್ಥಿ", "संकष्ट चतुर्थी"),
    ),
    _f(
        "Purnima",
        tithi="Purnima",
        ftype="worship",
        description="Full Moon day, auspicious for spiritual activities",
        labels=("Purnima Observance", "ಪೌರ್ಣಿಮಾ ಆಚರಣೆ", "पूर्णिमा पालनम्"),
        suppress_generic=[],
    ),
    _f(
        "Amavasya",
        tithi="Amavasya",
        ftype="ancestor",
        description="New Moon day, sacred for ancestor worship",
        labels=("Amavasya Observance", "ಅಮಾವಾಸ್ಯೆ ಆಚರಣೆ", "अमावास्या पालनम्"),
    ),
]
# Mark generics for suppress logic.
for _entry in RECURRING_OBSERVANCES:
    if _entry["name"] in {"Purnima", "Amavasya", "Ekadashi"}:
        _entry["generic"] = True
RECURRING_OBSERVANCES[2]["skip_if_festivals"] = ["Ganesh Chaturthi"]  # Sankashta


def base_lunar_month_name(lunar_month: str | None) -> str:
    name = str(lunar_month or "").strip()
    if name.lower().startswith("adhika "):
        return name.split(" ", 1)[1].strip()
    return name


def _normalize_month(name: str | None) -> str:
    raw = base_lunar_month_name(name)
    if not raw:
        return ""
    for canonical, aliases in MONTH_ALIASES.items():
        if raw == canonical or raw in aliases:
            return canonical
    return raw


def _normalize_nakshatra(name: str | None) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    for canonical, aliases in NAKSHATRA_ALIASES.items():
        if raw == canonical or raw in aliases:
            return canonical
    return raw


def _months_match(candidate_months: Sequence[str], lunar_month: str | None) -> bool:
    if not candidate_months:
        return True
    month = _normalize_month(lunar_month)
    if not month:
        return False
    accepted = {_normalize_month(m) for m in candidate_months}
    return month in accepted


def _month_rule_matches(entry: Dict, amanta: str | None, purnimanta: str | None) -> bool:
    """Match Amanta ``months`` against amanta, or ``purnimanta_months`` against purnimanta.

    Do not cross-compare Amanta month names against the purnimanta label — that
    false-positives Krishna-paksha festivals one month early.
    """
    months = entry.get("months") or []
    p_months = entry.get("purnimanta_months") or []
    if not months and not p_months:
        return True
    if months and _months_match(months, amanta):
        return True
    if p_months and purnimanta and _months_match(p_months, purnimanta):
        return True
    return False


def _nakshatra_matches(entry: Dict, nakshatra_name: str) -> bool:
    wanted = entry.get("nakshatras") or []
    mode = entry.get("nakshatra_mode") or "preferred"
    if not wanted or mode == "ignore":
        return True
    current = _normalize_nakshatra(nakshatra_name)
    accepted = {_normalize_nakshatra(n) for n in wanted}
    if mode == "required":
        return bool(current) and current in accepted
    # preferred: do not block match; caller may annotate
    return True


def _tithi_number(tithi_name: str, tithi_data: Dict) -> int:
    if tithi_data.get("number"):
        try:
            return int(tithi_data["number"])
        except (TypeError, ValueError):
            pass
    if tithi_name == "Purnima":
        return 15
    if tithi_name == "Amavasya":
        return 15
    try:
        return TITHIS.index(tithi_name) + 1
    except ValueError:
        return 0


def _is_malayalam_chingam(jd: float) -> bool:
    sun_long = get_sidereal_position(jd, swe.SUN) % 360
    return 120.0 <= sun_long < 150.0


def _sun_sign_index(jd: float) -> int:
    return int((get_sidereal_position(jd, swe.SUN) % 360) / 30)


def _solar_sankranti_into(jd: float, target_sign: int) -> bool:
    today = _sun_sign_index(jd)
    yesterday = _sun_sign_index(jd - 1.0)
    return today == target_sign and yesterday != target_sign


def _festival_payload(entry: Dict, *, note: str | None = None) -> Dict:
    payload = {
        "name": entry["name"],
        "type": entry.get("type", "festival"),
        "importance": entry.get("importance", "major"),
        "description": entry.get("description", ""),
        "observances": list(entry.get("observances") or []),
        "benefits": list(entry.get("benefits") or []),
        "typical_nakshatras": list(entry.get("nakshatras") or []),
        "catalog": True,
    }
    if note:
        payload["match_note"] = note
    return payload


def _match_special_rule(
    entry: Dict,
    *,
    tithi_name: str,
    paksha: str,
    amanta: str | None,
    weekday: str,
    nakshatra_name: str,
    jd: float | None,
    tithi_data: Dict,
) -> bool:
    rule = entry.get("rule")
    if not rule:
        return True
    if rule == "makar_sankranti":
        return jd is not None and _solar_sankranti_into(jd, 9)
    if rule == "mesha_sankranti":
        return jd is not None and _solar_sankranti_into(jd, 0)
    if rule == "onam":
        return (
            jd is not None
            and _normalize_nakshatra(nakshatra_name) == "Shravana"
            and _is_malayalam_chingam(jd)
        )
    if rule == "varalakshmi":
        # Friday in Shravana Shukla before Purnima (within 6 tithis).
        if weekday != "Friday":
            return False
        if paksha != "Shukla":
            return False
        if not _months_match(["Shravana"], amanta):
            return False
        num = _tithi_number(tithi_name, tithi_data)
        return 1 <= num <= 14 and (15 - num) <= 6
    return False


def match_major_festivals(
    *,
    tithi_name: str,
    paksha: str,
    lunar_month: str | None,
    lunar_month_purnimanta: str | None = None,
    nakshatra_name: str = "",
    weekday: str = "",
    jd: float | None = None,
    tithi_data: Dict | None = None,
) -> List[Dict]:
    """Return matched major festivals for the day."""
    matched: List[Dict] = []
    tithi_data = tithi_data or {}
    amanta = base_lunar_month_name(lunar_month)
    purnimanta = base_lunar_month_name(lunar_month_purnimanta)

    for entry in MAJOR_FESTIVAL_CATALOG:
        rule = entry.get("rule")
        if rule:
            if _match_special_rule(
                entry,
                tithi_name=tithi_name,
                paksha=paksha,
                amanta=amanta,
                weekday=weekday,
                nakshatra_name=nakshatra_name,
                jd=jd,
                tithi_data=tithi_data,
            ):
                matched.append(_festival_payload(entry))
            continue

        if entry.get("tithi") and entry["tithi"] != tithi_name:
            continue
        if entry.get("paksha") and entry["paksha"] != paksha:
            continue
        if entry.get("weekday") and entry["weekday"] != weekday:
            continue
        if not _month_rule_matches(entry, amanta, purnimanta):
            continue
        if not _nakshatra_matches(entry, nakshatra_name):
            continue

        note = None
        wanted = entry.get("nakshatras") or []
        if wanted and entry.get("nakshatra_mode") == "preferred":
            current = _normalize_nakshatra(nakshatra_name)
            accepted = {_normalize_nakshatra(n) for n in wanted}
            if current and current not in accepted:
                note = f"Typical nakshatra {', '.join(wanted)}; today {nakshatra_name or 'n/a'}"
        matched.append(_festival_payload(entry, note=note))

    return matched


def match_recurring_observances(
    *,
    tithi_name: str,
    paksha: str,
    major_names: Iterable[str],
) -> List[Dict]:
    majors = set(major_names)
    suppressed: Set[str] = set()
    for entry in MAJOR_FESTIVAL_CATALOG:
        if entry["name"] in majors:
            suppressed.update(entry.get("suppress_generic") or [])

    results: List[Dict] = []
    for entry in RECURRING_OBSERVANCES:
        if entry.get("tithi") and entry["tithi"] != tithi_name:
            continue
        if entry.get("paksha") and entry["paksha"] != paksha:
            continue
        if entry.get("generic") and entry["name"] in suppressed:
            continue
        skip_if = entry.get("skip_if_festivals") or []
        if skip_if and any(name in majors for name in skip_if):
            continue
        results.append(_festival_payload(entry))
    return results


def festival_label_map() -> Dict[str, tuple]:
    labels: Dict[str, tuple] = {}
    for entry in MAJOR_FESTIVAL_CATALOG + RECURRING_OBSERVANCES:
        labels[entry["name"]] = tuple(entry.get("labels") or (entry["name"],) * 3)
    return labels


def detect_day_festivals(
    *,
    tithi_data: Dict,
    nakshatra: Dict,
    jd: float | None = None,
    lunar_month: str | None = None,
    lunar_month_purnimanta: str | None = None,
    weekday: str | None = None,
) -> List[Dict]:
    """Full day festival list: majors first, then recurring observances."""
    tithi_name = str(tithi_data.get("name") or "")
    paksha = str(tithi_data.get("paksha") or "")
    nakshatra_name = str(nakshatra.get("name") or "").strip()

    majors = match_major_festivals(
        tithi_name=tithi_name,
        paksha=paksha,
        lunar_month=lunar_month,
        lunar_month_purnimanta=lunar_month_purnimanta,
        nakshatra_name=nakshatra_name,
        weekday=str(weekday or ""),
        jd=jd,
        tithi_data=tithi_data,
    )
    recurring = match_recurring_observances(
        tithi_name=tithi_name,
        paksha=paksha,
        major_names=[item["name"] for item in majors],
    )

    combined: List[Dict] = []
    seen: Set[str] = set()
    for item in majors + recurring:
        name = item.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        combined.append(item)
    return combined
