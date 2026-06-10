"""Indian GST state codes (2-digit) and a resolver for place-of-supply.

GSTR-1 needs the place of supply as the 2-digit state code. Invoices store it as
free text (a name, a "code-name" string, or sometimes already a code), so we
normalise here, falling back to the recipient GSTIN's first two digits.
"""
from __future__ import annotations

# Official GST state / UT codes.
STATE_CODES: dict[str, str] = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre Jurisdiction",
}

_VALID_CODES = set(STATE_CODES.keys())


def _norm(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


# Normalised state name -> code, plus a couple of common aliases.
_NAME_TO_CODE: dict[str, str] = {_norm(name): code for code, name in STATE_CODES.items()}
_NAME_TO_CODE.update({
    _norm("Pondicherry"): "34",
    _norm("Orissa"): "21",
    _norm("Uttaranchal"): "05",
    _norm("Andhra Pradesh Old"): "37",
    _norm("Daman and Diu"): "26",
    _norm("Dadra and Nagar Haveli"): "26",
})


def resolve_state_code(place_of_supply: str | None, gstin: str | None = None) -> str:
    """Best-effort 2-digit state code from a free-text place of supply, with the
    recipient GSTIN's leading two digits as a fallback. Returns "" if unknown."""
    text = str(place_of_supply or "").strip()
    if text:
        # Leading 2 digits already a valid code (e.g. "29" or "29-Karnataka").
        head = text[:2]
        if head in _VALID_CODES:
            return head
        # Otherwise treat the (alnum-normalised) text as a state name.
        key = _norm(text)
        if key in _NAME_TO_CODE:
            return _NAME_TO_CODE[key]
        # "Code - Name" forms where the head wasn't numeric.
        for sep in ("-", ":", " "):
            if sep in text:
                left = text.split(sep, 1)[0].strip()
                if left in _VALID_CODES:
                    return left
                lkey = _norm(left)
                if lkey in _NAME_TO_CODE:
                    return _NAME_TO_CODE[lkey]
    gstin = str(gstin or "").strip()
    if len(gstin) >= 2 and gstin[:2] in _VALID_CODES:
        return gstin[:2]
    return ""


def state_label(code: str) -> str:
    code = str(code or "").strip()
    name = STATE_CODES.get(code)
    return f"{code}-{name}" if name else code
