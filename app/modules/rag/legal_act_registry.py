import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LegalActMatch:
    key: str
    canonical_name: str
    matched_alias: str
    aliases: tuple[str, ...]

    @property
    def metadata_regex(self) -> str:
        values = [self.canonical_name, *self.aliases]
        escaped = sorted({re.escape(value) for value in values if value}, key=len, reverse=True)
        return "|".join(escaped)


_LEGAL_ACTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "bnss",
        "Bharatiya Nagarik Suraksha Sanhita, 2023",
        ("Bharatiya Nagarik Suraksha Sanhita", "BNSS", "BNSS 2023"),
    ),
    (
        "bns",
        "Bharatiya Nyaya Sanhita, 2023",
        ("Bharatiya Nyaya Sanhita", "BNS", "BNS 2023"),
    ),
    (
        "bsa",
        "Bharatiya Sakshya Adhiniyam, 2023",
        ("Bharatiya Sakshya Adhiniyam", "BSA", "BSA 2023"),
    ),
    (
        "crpc",
        "Code of Criminal Procedure, 1973",
        ("Code of Criminal Procedure", "CrPC", "CRPC", "Cr.P.C."),
    ),
    (
        "ipc",
        "Indian Penal Code, 1860",
        ("Indian Penal Code", "IPC"),
    ),
    (
        "cpc",
        "Code of Civil Procedure, 1908",
        ("Code of Civil Procedure", "CPC", "C.P.C."),
    ),
    (
        "evidence_act",
        "Indian Evidence Act, 1872",
        ("Indian Evidence Act", "Evidence Act"),
    ),
    (
        "negotiable_instruments",
        "Negotiable Instruments Act, 1881",
        ("Negotiable Instruments Act", "NI Act", "N.I. Act", "cheque bounce", "cheque dishonour"),
    ),
    (
        "cgst",
        "Central Goods and Services Tax Act, 2017",
        ("Central Goods and Services Tax Act", "CGST Act", "GST Act", "GST"),
    ),
    (
        "income_tax",
        "Income-tax Act, 1961",
        ("Income Tax Act", "Income-tax Act", "IT Act 1961"),
    ),
    (
        "contract_act",
        "Indian Contract Act, 1872",
        ("Indian Contract Act", "Contract Act"),
    ),
    (
        "arbitration_act",
        "Arbitration and Conciliation Act, 1996",
        ("Arbitration and Conciliation Act", "Arbitration Act"),
    ),
    (
        "companies_act",
        "Companies Act, 2013",
        ("Companies Act", "company law"),
    ),
    (
        "llp_act",
        "Limited Liability Partnership Act, 2008",
        ("Limited Liability Partnership Act", "LLP Act"),
    ),
    (
        "dpdp",
        "Digital Personal Data Protection Act, 2023",
        ("Digital Personal Data Protection Act", "DPDP Act", "DPDPA"),
    ),
    (
        "information_technology",
        "Information Technology Act, 2000",
        ("Information Technology Act", "IT Act 2000"),
    ),
    (
        "pmla",
        "Prevention of Money Laundering Act, 2002",
        ("Prevention of Money Laundering Act", "PMLA"),
    ),
    (
        "ndps",
        "Narcotic Drugs and Psychotropic Substances Act, 1985",
        ("Narcotic Drugs and Psychotropic Substances Act", "NDPS Act", "NDPS"),
    ),
    (
        "uapa",
        "Unlawful Activities (Prevention) Act, 1967",
        ("Unlawful Activities Prevention Act", "UAPA"),
    ),
)


_GENERIC_LEGAL_TRIGGER_TERMS = (
    "act",
    "section",
    "statute",
    "rule",
    "regulation",
    "bare act",
)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.lower())
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


def detect_legal_act(query: str) -> LegalActMatch | None:
    text = (query or "").strip()
    if not text:
        return None

    candidates: list[tuple[int, str, str, str, tuple[str, ...]]] = []
    for key, canonical_name, aliases in _LEGAL_ACTS:
        for alias in (canonical_name, *aliases):
            candidates.append((len(alias), key, canonical_name, alias, aliases))

    for _, key, canonical_name, alias, aliases in sorted(candidates, reverse=True):
        if _alias_pattern(alias).search(text):
            return LegalActMatch(
                key=key,
                canonical_name=canonical_name,
                matched_alias=alias,
                aliases=aliases,
            )

    return None


def legal_act_metadata_filter(match: LegalActMatch) -> dict[str, str]:
    return {"$regex": match.metadata_regex, "$options": "i"}


def should_trigger_jit(query: str) -> bool:
    text = (query or "").lower()
    if detect_legal_act(text):
        return True
    return any(term in text for term in _GENERIC_LEGAL_TRIGGER_TERMS)
